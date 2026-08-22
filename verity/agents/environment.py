"""Environment Agent and its isolated execution backends.

The Environment Agent clones and executes **arbitrary third-party code**. That work never
runs on the host: :class:`DockerSandboxBackend` is the local-first backend and puts every
phase inside a throwaway container whose only writable mount is one fresh temp directory.

Three backends implement :class:`verity.interfaces.SandboxBackend`:

* :class:`DockerSandboxBackend` — local default. ``docker run --rm`` per phase.
* :class:`CloudRunJobBackend` — one fresh Cloud Run Job task per attempt. Cloud Run runs
  containers, so this is the same execution model with a different scheduler.
* :class:`LocalSandboxBackend` — raw host subprocesses. **Not an isolation boundary.** It
  exists because it is what runs *inside* the sandbox container image, where the container
  is the boundary; selecting it as the top-level backend requires an explicit opt-in.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from verity.interfaces import SandboxBackend, SandboxUnavailableError
from verity.models import (
    EnvironmentResult,
    ParsedClaim,
    PatchOperation,
    SandboxRequest,
    SandboxRun,
)
from verity.security import safe_repo_path, validate_repository_url

logger = logging.getLogger(__name__)

#: Tag of the sandbox runtime image built from ``Dockerfile.runner``.
DEFAULT_SANDBOX_IMAGE = "verity-sandbox-runner:1"

#: Absolute paths *inside* the container. The bind mount is the only writable location.
CONTAINER_WORKSPACE = "/work"
CONTAINER_REPO = "/work/repo"
CONTAINER_VENV_PYTHON = "/work/venv/bin/python"


class SandboxStore(Protocol):
    async def create_sandbox_run(self, run: SandboxRun) -> None: ...

    async def get_sandbox_run(self, run_id: str) -> SandboxRun | None: ...


def apply_patch_operations(repo: Path, patches: list[PatchOperation]) -> None:
    for patch in patches:
        target = safe_repo_path(repo, patch.path)
        if patch.kind == "write_file":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(patch.new_text, encoding="utf-8")
            continue
        if not target.is_file():
            raise ValueError(f"patch target does not exist: {patch.path}")
        if patch.old_text is None or not patch.old_text:
            raise ValueError("replace_text requires non-empty old_text")
        original = target.read_text(encoding="utf-8")
        occurrences = original.count(patch.old_text)
        if occurrences != 1:
            raise ValueError(
                f"replace_text expected exactly one match in {patch.path}, found {occurrences}"
            )
        target.write_text(original.replace(patch.old_text, patch.new_text, 1), encoding="utf-8")


def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _normalize_command(command: list[str], python: str | Path) -> list[str]:
    """Rewrite an interpreter-relative argv onto a specific Python, or reject it.

    The allowlist is deliberate: a claim's evaluation step is a Python entry point, and
    anything else — a shell, a downloader, a package manager we did not provision — is a
    sign the plan drifted from what the source actually documented.
    """
    if not command:
        raise ValueError("evaluation command is empty")
    if any("\x00" in part or len(part) > 2000 for part in command):
        raise ValueError("command contains an invalid argument")
    executable = Path(command[0]).name.lower()
    if executable in {"python", "python3", "python.exe"}:
        return [str(python), *command[1:]]
    if executable in {"pytest", "pytest.exe"}:
        return [str(python), "-m", "pytest", *command[1:]]
    if executable in {"pip", "pip3", "pip.exe"}:
        return [str(python), "-m", "pip", *command[1:]]
    raise ValueError(f"executable {command[0]!r} is outside the sandbox allowlist")


def _run_process(
    command: list[str],
    *,
    cwd: Path,
    timeout: int,
    max_chars: int,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        shell=False,
        check=False,
    )
    return completed.returncode, completed.stdout[-max_chars:], completed.stderr[-max_chars:]


def _extract_metric(
    output: str, metric: str, pattern: str | None
) -> tuple[float | None, str | None]:
    try:
        matcher = (
            re.search(pattern, output, flags=re.IGNORECASE | re.MULTILINE) if pattern else None
        )
    except re.error:
        matcher = None
    if matcher is None:
        flexible_metric = re.sub(r"\\\s+", r"\\s+", re.escape(metric))
        matcher = re.search(
            rf"{flexible_metric}[^\n\d+-]{{0,80}}([+-]?(?:\d+(?:\.\d*)?|\.\d+))",
            output,
            flags=re.IGNORECASE,
        )
    if matcher is None:
        return None, None
    value_text = matcher.groupdict().get("value") or matcher.group(1)
    try:
        value = float(value_text.replace(",", ""))
    except ValueError:
        return None, None
    evidence = output[max(0, matcher.start() - 150) : matcher.end() + 150]
    return value, evidence.strip()


def _diagnostic_files(repo: Path, stderr: str) -> dict[str, str]:
    """Pull the source files named by a traceback so the Debug Agent sees real code.

    Container paths (``/work/repo/...``) are translated back to the host workspace.
    """
    found: dict[str, str] = {}
    for candidate in re.findall(r'File "([^"]+)"', stderr):
        text = candidate
        if text.startswith(CONTAINER_REPO + "/"):
            text = text[len(CONTAINER_REPO) + 1 :]
        path = Path(text)
        if path.is_absolute():
            try:
                path.resolve().relative_to(repo.resolve())
            except (OSError, ValueError):
                continue
        else:
            path = repo / path
        try:
            resolved = path.resolve()
            relative = resolved.relative_to(repo.resolve()).as_posix()
        except (OSError, ValueError):
            continue
        if relative in found or not resolved.is_file() or len(found) >= 6:
            continue
        try:
            found[relative] = resolved.read_text(encoding="utf-8", errors="replace")[:15_000]
        except OSError:
            continue
    return found


def _default_install_commands(workdir: Path) -> list[list[str]]:
    if (workdir / "requirements.txt").is_file():
        return [["python", "-m", "pip", "install", "-r", "requirements.txt"]]
    if (workdir / "pyproject.toml").is_file() or (workdir / "setup.py").is_file():
        return [["python", "-m", "pip", "install", "."]]
    return []


# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DockerLimits:
    """Resource ceilings applied to every sandbox container."""

    memory: str = "4g"
    cpus: str = "2"
    pids: int = 512
    tmpfs_size: str = "1g"


class DockerSandboxBackend(SandboxBackend):
    """Run each verification phase in a throwaway container.

    Four phases, each its own ``docker run --rm``:

    ==========  =========  ==================================================
    Phase       Network    Why
    ==========  =========  ==================================================
    clone       bridge     Fetch the declared repository.
    venv        none       Create the interpreter; nothing to download.
    install     bridge     Install the *declared* dependencies only.
    evaluate    **none**   The benchmark itself never touches the network.
    ==========  =========  ==================================================

    Every container gets ``--cap-drop ALL``, ``--security-opt no-new-privileges``, a
    read-only root filesystem with a size-capped ``/tmp`` tmpfs, pid/memory/cpu limits,
    and exactly one bind mount: a fresh host temp directory at ``/work``. No Docker
    socket, no host paths, no image reuse between jobs.

    Patches are applied on the host inside that same temp directory between the clone and
    install phases, which is why the mount is read-write rather than read-only.
    """

    def __init__(
        self,
        *,
        image: str = DEFAULT_SANDBOX_IMAGE,
        timeout_seconds: int = 900,
        max_output_chars: int = 100_000,
        allowed_repo_hosts: tuple[str, ...] = ("github.com",),
        dockerfile: Path | None = None,
        auto_build: bool = True,
        limits: DockerLimits | None = None,
        docker_binary: str = "docker",
        run_as_host_user: bool | None = None,
    ) -> None:
        self._image = image
        self._timeout = timeout_seconds
        self._max_chars = max_output_chars
        self._allowed_repo_hosts = allowed_repo_hosts
        self._dockerfile = dockerfile or Path("Dockerfile.runner")
        self._auto_build = auto_build
        self._limits = limits or DockerLimits()
        self._docker = docker_binary
        # On Linux a bind mount keeps host ownership, so the container must run as the
        # host uid to write into the workspace. Docker Desktop's mounts are already
        # world-writable, so there the image's own non-root user is used unchanged.
        self._run_as_host_user = os.name != "nt" if run_as_host_user is None else run_as_host_user
        self._ready = False

    # --- preflight -----------------------------------------------------------

    async def preflight(self) -> None:
        if self._ready:
            return
        await asyncio.to_thread(self._preflight_sync)
        self._ready = True

    def _preflight_sync(self) -> None:
        if shutil.which(self._docker) is None:
            raise SandboxUnavailableError(
                "Docker is not installed or not on PATH. Verity executes untrusted "
                "third-party code and refuses to run it directly on the host. "
                "Install Docker Desktop (or the Docker Engine) and try again."
            )
        try:
            probe = subprocess.run(
                [self._docker, "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SandboxUnavailableError(f"`docker info` did not respond: {exc}") from exc
        if probe.returncode != 0:
            raise SandboxUnavailableError(
                "The Docker daemon is not reachable. Start Docker Desktop (or "
                "`systemctl start docker`) and retry.\n"
                f"`docker info` said: {(probe.stderr or probe.stdout).strip()[:800]}"
            )
        logger.info("Docker daemon %s is available", probe.stdout.strip())
        self._ensure_image()
        self._verify_mount()

    def _image_exists(self) -> bool:
        result = subprocess.run(
            [self._docker, "image", "inspect", self._image],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        return result.returncode == 0

    def _ensure_image(self) -> None:
        if self._image_exists():
            return
        if not self._auto_build:
            raise SandboxUnavailableError(
                f"Sandbox image {self._image!r} is missing. Build it with: "
                f"docker build -f {self._dockerfile} -t {self._image} ."
            )
        if not self._dockerfile.is_file():
            raise SandboxUnavailableError(
                f"Sandbox image {self._image!r} is missing and {self._dockerfile} was not "
                "found. Run Verity from the repository root, or build the image yourself."
            )
        logger.info("Building sandbox image %s from %s", self._image, self._dockerfile)
        build = subprocess.run(
            [self._docker, "build", "-f", str(self._dockerfile), "-t", self._image, "."],
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
        if build.returncode != 0:
            raise SandboxUnavailableError(
                f"Building {self._image!r} failed:\n{(build.stderr or build.stdout)[-4000:]}"
            )

    def _verify_mount(self) -> None:
        """Confirm the bind mount actually reaches the container.

        On Windows this is where an unshared drive shows up, and it is far cheaper to
        find out here than three minutes into a benchmark.
        """
        with tempfile.TemporaryDirectory(prefix="verity-preflight-") as temp:
            workspace = Path(temp)
            (workspace / "sentinel").write_text("ok", encoding="utf-8")
            code, stdout, stderr = self._docker_run(
                workspace,
                ["python", "-c", "print(open('/work/sentinel').read())"],
                network="none",
                workdir=CONTAINER_WORKSPACE,
                timeout=180,
            )
            if code != 0 or "ok" not in stdout:
                raise SandboxUnavailableError(
                    "Docker could not bind-mount the sandbox workspace. On Windows, share "
                    "the drive holding your TEMP directory in Docker Desktop → Settings → "
                    f"Resources → File sharing.\nexit={code}\n{(stderr or stdout)[:1500]}"
                )

    # --- container execution -------------------------------------------------

    def _docker_run(
        self,
        workspace: Path,
        argv: list[str],
        *,
        network: str,
        workdir: str,
        timeout: int,
    ) -> tuple[int, str, str]:
        name = f"verity-{uuid.uuid4().hex[:12]}"
        source = str(workspace.resolve()).replace("\\", "/")
        command = [
            self._docker,
            "run",
            "--rm",
            "--name",
            name,
            "--network",
            network,
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            str(self._limits.pids),
            "--memory",
            self._limits.memory,
            "--cpus",
            self._limits.cpus,
            "--read-only",
            "--tmpfs",
            f"/tmp:rw,exec,nosuid,size={self._limits.tmpfs_size}",
            "--mount",
            f"type=bind,source={source},target={CONTAINER_WORKSPACE}",
            "--workdir",
            workdir,
            "--env",
            "HOME=/tmp",
            "--env",
            "PYTHONUNBUFFERED=1",
            "--env",
            "PIP_DISABLE_PIP_VERSION_CHECK=1",
            "--env",
            "PIP_NO_CACHE_DIR=1",
            "--env",
            "GIT_TERMINAL_PROMPT=0",
            "--entrypoint",
            argv[0],
        ]
        if self._run_as_host_user and hasattr(os, "getuid"):
            command += ["--user", f"{os.getuid()}:{os.getgid()}"]  # type: ignore[attr-defined]
        command += [self._image, *argv[1:]]
        try:
            return _run_process(
                command,
                cwd=workspace,
                timeout=timeout,
                max_chars=self._max_chars,
            )
        except subprocess.TimeoutExpired:
            subprocess.run(
                [self._docker, "rm", "--force", name],
                capture_output=True,
                timeout=120,
                check=False,
            )
            raise

    # --- SandboxBackend ------------------------------------------------------

    async def run(
        self,
        job_id: str,
        parsed_claim: ParsedClaim,
        patches: list[PatchOperation],
        command_override: list[str] | None,
    ) -> EnvironmentResult:
        await self.preflight()
        return await asyncio.to_thread(self._run_sync, parsed_claim, patches, command_override)

    def _run_sync(
        self,
        parsed_claim: ParsedClaim,
        patches: list[PatchOperation],
        command_override: list[str] | None,
    ) -> EnvironmentResult:
        started = time.monotonic()
        execution = parsed_claim.execution

        def elapsed() -> float:
            return time.monotonic() - started

        if execution.repository_url is None:
            return EnvironmentResult(
                succeeded=False,
                phase="clone",
                stderr="No associated repository was present in the source.",
                duration_seconds=elapsed(),
            )
        try:
            repo_url = validate_repository_url(
                str(execution.repository_url), self._allowed_repo_hosts
            )
        except ValueError as exc:
            return EnvironmentResult(
                succeeded=False,
                phase="clone",
                stderr=str(exc),
                duration_seconds=elapsed(),
            )

        with tempfile.TemporaryDirectory(prefix="verity-", ignore_cleanup_errors=True) as temp:
            workspace = Path(temp)
            repo = workspace / "repo"
            repo.mkdir()

            # 1. clone — the only phase allowed to reach the repository host.
            clone = ["git", "clone", "--depth", "1"]
            if execution.revision:
                clone += ["--branch", execution.revision]
            clone += [repo_url, CONTAINER_REPO]
            try:
                code, stdout, stderr = self._docker_run(
                    workspace,
                    clone,
                    network="bridge",
                    workdir=CONTAINER_WORKSPACE,
                    timeout=min(self._timeout, 600),
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                return EnvironmentResult(
                    succeeded=False,
                    phase="clone",
                    stderr=f"{type(exc).__name__}: {exc}",
                    duration_seconds=elapsed(),
                )
            if code:
                return EnvironmentResult(
                    succeeded=False,
                    exit_code=code,
                    phase="clone",
                    stdout=stdout,
                    stderr=stderr,
                    duration_seconds=elapsed(),
                )

            # 2. patch — on the host, inside the mounted workspace only.
            try:
                apply_patch_operations(repo, patches)
            except (OSError, ValueError) as exc:
                return EnvironmentResult(
                    succeeded=False,
                    phase="install",
                    stderr=f"Patch application failed: {exc}",
                    duration_seconds=elapsed(),
                )

            host_workdir = safe_repo_path(repo, execution.working_directory)
            relative = host_workdir.resolve().relative_to(repo.resolve()).as_posix()
            container_workdir = (
                CONTAINER_REPO if relative == "." else f"{CONTAINER_REPO}/{relative}"
            )

            combined_stdout = stdout
            combined_stderr = stderr

            def accumulate(out: str, err: str) -> None:
                nonlocal combined_stdout, combined_stderr
                combined_stdout = (combined_stdout + "\n" + out)[-self._max_chars :]
                combined_stderr = (combined_stderr + "\n" + err)[-self._max_chars :]

            # 3. virtual environment — offline; the image already carries Python.
            try:
                code, out, err = self._docker_run(
                    workspace,
                    ["python", "-m", "venv", "/work/venv"],
                    network="none",
                    workdir=CONTAINER_WORKSPACE,
                    timeout=min(self._timeout, 300),
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                code, out, err = -1, "", f"{type(exc).__name__}: {exc}"
            accumulate(out, err)
            if code:
                return EnvironmentResult(
                    succeeded=False,
                    exit_code=code,
                    phase="install",
                    stdout=combined_stdout,
                    stderr=combined_stderr,
                    duration_seconds=elapsed(),
                )

            # 4. install — network on, but only the declared commands run.
            install_commands = execution.install_commands or _default_install_commands(host_workdir)
            for install in install_commands:
                try:
                    code, out, err = self._docker_run(
                        workspace,
                        _normalize_command(install, CONTAINER_VENV_PYTHON),
                        network="bridge",
                        workdir=container_workdir,
                        timeout=self._timeout,
                    )
                except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                    code, out, err = -1, "", f"{type(exc).__name__}: {exc}"
                accumulate(out, err)
                if code:
                    return EnvironmentResult(
                        succeeded=False,
                        exit_code=code,
                        phase="install",
                        stdout=combined_stdout,
                        stderr=combined_stderr,
                        diagnostic_files=_diagnostic_files(repo, err),
                        duration_seconds=elapsed(),
                    )

            # 5. evaluate — no network at all. A benchmark that needs to phone home
            #    during scoring is not a reproducible benchmark.
            evaluation = command_override or execution.evaluation_command
            try:
                code, out, err = self._docker_run(
                    workspace,
                    _normalize_command(evaluation, CONTAINER_VENV_PYTHON),
                    network="none",
                    workdir=container_workdir,
                    timeout=self._timeout,
                )
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                code, out, err = -1, "", f"{type(exc).__name__}: {exc}"
            accumulate(out, err)
            actual, evidence = _extract_metric(
                out + "\n" + err,
                parsed_claim.claim.metric,
                execution.result_pattern,
            )
            return EnvironmentResult(
                succeeded=code == 0,
                exit_code=code,
                phase="metric" if code == 0 else "evaluate",
                stdout=combined_stdout,
                stderr=combined_stderr,
                actual_value=actual,
                metric_evidence=evidence,
                diagnostic_files=_diagnostic_files(repo, err),
                duration_seconds=elapsed(),
                sandbox_execution=f"docker:{self._image}",
            )


# ---------------------------------------------------------------------------
# Host subprocesses (inside-the-container use only)
# ---------------------------------------------------------------------------


class LocalSandboxBackend(SandboxBackend):
    """Run the phases as plain host subprocesses.

    **This is not a security boundary.** It is the body of the sandbox container: the
    Cloud Run sandbox image runs exactly this code, and there the container around it is
    the boundary. Choosing it as Verity's top-level backend requires setting
    ``VERITY_SANDBOX_BACKEND=host_subprocess`` by hand, and the production config
    validator rejects it outright.
    """

    def __init__(
        self,
        *,
        timeout_seconds: int = 900,
        max_output_chars: int = 100_000,
        allowed_repo_hosts: tuple[str, ...] = ("github.com",),
    ) -> None:
        self._timeout = timeout_seconds
        self._max_chars = max_output_chars
        self._allowed_repo_hosts = allowed_repo_hosts

    async def run(
        self,
        job_id: str,
        parsed_claim: ParsedClaim,
        patches: list[PatchOperation],
        command_override: list[str] | None,
    ) -> EnvironmentResult:
        return await asyncio.to_thread(self._run_sync, parsed_claim, patches, command_override)

    def _run_sync(
        self,
        parsed_claim: ParsedClaim,
        patches: list[PatchOperation],
        command_override: list[str] | None,
    ) -> EnvironmentResult:
        started = time.monotonic()
        execution = parsed_claim.execution
        if execution.repository_url is None:
            return EnvironmentResult(
                succeeded=False,
                phase="clone",
                stderr="No associated repository was present in the source.",
                duration_seconds=time.monotonic() - started,
            )
        try:
            repo_url = validate_repository_url(
                str(execution.repository_url), self._allowed_repo_hosts
            )
        except ValueError as exc:
            return EnvironmentResult(
                succeeded=False,
                phase="clone",
                stderr=str(exc),
                duration_seconds=time.monotonic() - started,
            )

        with tempfile.TemporaryDirectory(prefix="verity-") as temp:
            root = Path(temp)
            repo = root / "repo"
            clone = ["git", "clone", "--depth", "1"]
            if execution.revision:
                clone.extend(["--branch", execution.revision])
            clone.extend([repo_url, str(repo)])
            try:
                code, stdout, stderr = _run_process(
                    clone,
                    cwd=root,
                    timeout=min(self._timeout, 300),
                    max_chars=self._max_chars,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                return EnvironmentResult(
                    succeeded=False,
                    phase="clone",
                    stderr=str(exc),
                    duration_seconds=time.monotonic() - started,
                )
            if code:
                return EnvironmentResult(
                    succeeded=False,
                    exit_code=code,
                    phase="clone",
                    stdout=stdout,
                    stderr=stderr,
                    duration_seconds=time.monotonic() - started,
                )
            try:
                apply_patch_operations(repo, patches)
            except (OSError, ValueError) as exc:
                return EnvironmentResult(
                    succeeded=False,
                    phase="install",
                    stderr=f"Patch application failed: {exc}",
                    duration_seconds=time.monotonic() - started,
                )

            workdir = safe_repo_path(repo, execution.working_directory)
            venv = root / "venv"
            code, venv_stdout, venv_stderr = _run_process(
                [sys.executable, "-m", "venv", str(venv)],
                cwd=root,
                timeout=min(self._timeout, 180),
                max_chars=self._max_chars,
            )
            if code:
                return EnvironmentResult(
                    succeeded=False,
                    exit_code=code,
                    phase="install",
                    stdout=venv_stdout,
                    stderr=venv_stderr,
                    duration_seconds=time.monotonic() - started,
                )
            python = _venv_python(venv)
            install_commands = execution.install_commands or _default_install_commands(workdir)

            combined_stdout = stdout
            combined_stderr = stderr
            clean_env = {
                "PATH": os.pathsep.join([str(python.parent), os.environ.get("PATH", "")]),
                "PYTHONUNBUFFERED": "1",
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                "HOME": str(root / "home"),
                "TMPDIR": str(root / "tmp"),
            }
            (root / "home").mkdir()
            (root / "tmp").mkdir()
            for install in install_commands:
                try:
                    command = _normalize_command(install, python)
                    code, out, err = _run_process(
                        command,
                        cwd=workdir,
                        timeout=self._timeout,
                        max_chars=self._max_chars,
                        env=clean_env,
                    )
                except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                    code, out, err = -1, "", str(exc)
                combined_stdout = (combined_stdout + "\n" + out)[-self._max_chars :]
                combined_stderr = (combined_stderr + "\n" + err)[-self._max_chars :]
                if code:
                    return EnvironmentResult(
                        succeeded=False,
                        exit_code=code,
                        phase="install",
                        stdout=combined_stdout,
                        stderr=combined_stderr,
                        diagnostic_files=_diagnostic_files(repo, err),
                        duration_seconds=time.monotonic() - started,
                    )

            evaluation = command_override or execution.evaluation_command
            try:
                command = _normalize_command(evaluation, python)
                code, out, err = _run_process(
                    command,
                    cwd=workdir,
                    timeout=self._timeout,
                    max_chars=self._max_chars,
                    env=clean_env,
                )
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                code, out, err = -1, "", str(exc)
            combined_stdout = (combined_stdout + "\n" + out)[-self._max_chars :]
            combined_stderr = (combined_stderr + "\n" + err)[-self._max_chars :]
            actual, evidence = _extract_metric(
                out + "\n" + err,
                parsed_claim.claim.metric,
                execution.result_pattern,
            )
            return EnvironmentResult(
                succeeded=code == 0,
                exit_code=code,
                phase="metric" if code == 0 else "evaluate",
                stdout=combined_stdout,
                stderr=combined_stderr,
                actual_value=actual,
                metric_evidence=evidence,
                diagnostic_files=_diagnostic_files(repo, err),
                duration_seconds=time.monotonic() - started,
            )


# ---------------------------------------------------------------------------
# Cloud Run
# ---------------------------------------------------------------------------


class CloudRunJobBackend(SandboxBackend):
    """Launch one fresh Cloud Run Job task per attempt and read its stored result.

    The forward path from :class:`DockerSandboxBackend`: Cloud Run runs the same sandbox
    container, so what changes is who schedules it, not how the code is isolated.
    """

    def __init__(
        self,
        *,
        project: str,
        location: str,
        job_name: str,
        store: SandboxStore,
        timeout_seconds: int = 900,
    ) -> None:
        self._project = project
        self._location = location
        self._job_name = job_name
        self._store = store
        self._timeout = timeout_seconds

    async def run(
        self,
        job_id: str,
        parsed_claim: ParsedClaim,
        patches: list[PatchOperation],
        command_override: list[str] | None,
    ) -> EnvironmentResult:
        from google.cloud import run_v2

        run_id = uuid.uuid4().hex
        sandbox_request = SandboxRequest(
            run_id=run_id,
            job_id=job_id,
            parsed_claim=parsed_claim,
            patches=patches,
            command_override=command_override,
            timeout_seconds=self._timeout,
        )
        await self._store.create_sandbox_run(SandboxRun(request=sandbox_request))
        client = run_v2.JobsClient()
        name = client.job_path(self._project, self._location, self._job_name)
        override = run_v2.RunJobRequest.Overrides(
            container_overrides=[
                run_v2.RunJobRequest.Overrides.ContainerOverride(
                    env=[run_v2.EnvVar(name="VERITY_SANDBOX_RUN_ID", value=run_id)]
                )
            ],
            task_count=1,
            timeout={"seconds": self._timeout},
        )
        operation = await asyncio.to_thread(
            client.run_job,
            request=run_v2.RunJobRequest(name=name, overrides=override),
        )
        execution = await asyncio.to_thread(operation.result, timeout=self._timeout + 120)
        completed = await self._store.get_sandbox_run(run_id)
        if completed is None or completed.result is None:
            return EnvironmentResult(
                succeeded=False,
                phase="infrastructure",
                stderr="Cloud Run Job completed without a sandbox result record.",
                duration_seconds=0,
                sandbox_execution=getattr(execution, "name", None),
            )
        return completed.result.model_copy(
            update={"sandbox_execution": getattr(execution, "name", None)}
        )


class EnvironmentAgent:
    name = "environment"

    def __init__(self, backend: SandboxBackend) -> None:
        self._backend = backend

    async def preflight(self) -> None:
        await self._backend.preflight()

    async def run(
        self,
        job_id: str,
        parsed_claim: ParsedClaim,
        patches: list[PatchOperation],
        command_override: list[str] | None = None,
    ) -> EnvironmentResult:
        return await self._backend.run(job_id, parsed_claim, patches, command_override)
