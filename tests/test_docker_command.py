"""The sandbox `docker run` invocation, checked without a daemon.

``test_docker_sandbox.py`` proves the boundary holds by trying to escape it, but that needs
Docker running. These tests assert the flags that *create* the boundary are actually passed,
so a regression that silently drops ``--network none`` or ``--cap-drop ALL`` fails in CI
rather than only on a machine with Docker.
"""

from __future__ import annotations

import subprocess
from itertools import pairwise
from pathlib import Path

import pytest

from verity.agents.environment import (
    CONTAINER_REPO,
    CONTAINER_WORKSPACE,
    DockerLimits,
    DockerSandboxBackend,
)
from verity.interfaces import SandboxUnavailableError

COMMIT = "a" * 40


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Capture every argv the backend would hand to subprocess, and run nothing."""
    calls: list[list[str]] = []

    def fake_run_process(command, *, cwd, timeout, max_chars, env=None):
        calls.append(list(command))
        if "rev-parse" in command:
            return 0, COMMIT + "\n", ""
        return 0, "", ""

    monkeypatch.setattr("verity.agents.environment._run_process", fake_run_process)
    return calls


@pytest.fixture
def backend() -> DockerSandboxBackend:
    return DockerSandboxBackend(
        image="verity-sandbox-runner:test",
        limits=DockerLimits(memory="2g", cpus="1", pids=64, tmpfs_size="256m"),
    )


def invoke(backend: DockerSandboxBackend, tmp_path: Path, network: str) -> list[str]:
    backend._docker_run(
        tmp_path,
        ["python", "-c", "print(1)"],
        network=network,
        workdir=CONTAINER_WORKSPACE,
        timeout=60,
    )
    return []


def pairs(command: list[str]) -> set[tuple[str, str]]:
    return set(pairwise(command))


def test_every_container_drops_capabilities_and_privileges(backend, recorded, tmp_path) -> None:
    invoke(backend, tmp_path, "none")
    command = recorded[0]
    assert ("--cap-drop", "ALL") in pairs(command)
    assert ("--security-opt", "no-new-privileges") in pairs(command)
    assert "--read-only" in command
    assert "--rm" in command


def test_resource_limits_are_applied(backend, recorded, tmp_path) -> None:
    invoke(backend, tmp_path, "none")
    applied = pairs(recorded[0])
    assert ("--memory", "2g") in applied
    assert ("--cpus", "1") in applied
    assert ("--pids-limit", "64") in applied
    assert ("--tmpfs", "/tmp:rw,exec,nosuid,size=256m") in applied


def test_the_only_mount_is_the_fresh_workspace(backend, recorded, tmp_path) -> None:
    invoke(backend, tmp_path, "none")
    command = recorded[0]
    mounts = [value for flag, value in pairs(command) if flag in {"--mount", "-v", "--volume"}]
    assert len(mounts) == 1
    assert mounts[0] == (
        f"type=bind,source={str(tmp_path.resolve()).replace(chr(92), '/')}"
        f",target={CONTAINER_WORKSPACE}"
    )
    assert "/var/run/docker.sock" not in " ".join(command)


def test_network_mode_is_explicit_on_every_phase(backend, recorded, tmp_path) -> None:
    invoke(backend, tmp_path, "none")
    invoke(backend, tmp_path, "bridge")
    assert ("--network", "none") in pairs(recorded[0])
    assert ("--network", "bridge") in pairs(recorded[1])


def test_the_image_never_chooses_what_runs(backend, recorded, tmp_path) -> None:
    """--entrypoint is always overridden, so a tampered image cannot inject a command."""
    invoke(backend, tmp_path, "none")
    command = recorded[0]
    assert ("--entrypoint", "python") in pairs(command)
    assert command[-3:] == ["verity-sandbox-runner:test", "-c", "print(1)"]


def test_each_run_gets_a_unique_container_name(backend, recorded, tmp_path) -> None:
    invoke(backend, tmp_path, "none")
    invoke(backend, tmp_path, "none")
    names = [command[command.index("--name") + 1] for command in recorded if "--name" in command]
    assert len(names) == 2
    assert names[0] != names[1]
    assert all(name.startswith("verity-") for name in names)


def test_a_timeout_force_removes_the_container(
    backend, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    removed: list[list[str]] = []

    def timing_out(command, *, cwd, timeout, max_chars, env=None):
        raise subprocess.TimeoutExpired(command, timeout)

    def record_removal(command, **kwargs):
        removed.append(list(command))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("verity.agents.environment._run_process", timing_out)
    monkeypatch.setattr("verity.agents.environment.subprocess.run", record_removal)

    with pytest.raises(subprocess.TimeoutExpired):
        backend._docker_run(
            tmp_path,
            ["python", "-c", "pass"],
            network="none",
            workdir=CONTAINER_WORKSPACE,
            timeout=1,
        )
    assert removed and removed[0][:3] == ["docker", "rm", "--force"]


async def test_phases_use_the_intended_network_and_interpreter(
    backend, recorded, tmp_path, parsed_claim, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Walk a whole run: clone online, venv offline, install online, evaluate offline."""
    monkeypatch.setattr(DockerSandboxBackend, "preflight", _noop_preflight)
    parsed = parsed_claim.model_copy(deep=True)
    parsed.execution.install_commands = [["pip", "install", "-r", "requirements.txt"]]

    await backend.run("job-1", parsed, [], None)

    phases = [
        (
            command[command.index("--network") + 1],
            command[command.index(backend._image) + 1 :],
            command[command.index("--entrypoint") + 1],
        )
        for command in recorded
    ]
    networks = [network for network, _args, _entry in phases]
    assert networks == ["bridge", "none", "none", "bridge", "none"], (
        "clone and install may reach the network; the benchmark itself may not"
    )

    clone_args = phases[0][1]
    assert clone_args[-1] == CONTAINER_REPO
    assert phases[0][2] == "git"

    # The interpreter becomes the container entrypoint, so a `pip`/`pytest` argv from the
    # execution plan can never resolve to some other binary inside the image.
    revision_network, revision_args, revision_entrypoint = phases[1]
    assert revision_network == "none"
    assert revision_entrypoint == "git"
    assert revision_args == [
        "-c",
        f"safe.directory={CONTAINER_REPO}",
        "rev-parse",
        "--verify",
        "HEAD^{commit}",
    ]

    install_network, install_args, install_entrypoint = phases[3]
    assert install_entrypoint == "/work/venv/bin/python"
    assert install_args[:3] == ["-m", "pip", "install"]
    assert install_network == "bridge"

    evaluate_network, evaluate_args, evaluate_entrypoint = phases[4]
    assert evaluate_entrypoint == "/work/venv/bin/python"
    assert evaluate_args == ["evaluate.py"]
    assert evaluate_network == "none"


async def test_a_full_commit_uses_detached_fetch_instead_of_clone_branch(
    backend, recorded, parsed_claim, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(DockerSandboxBackend, "preflight", _noop_preflight)
    parsed = parsed_claim.model_copy(deep=True)
    parsed.execution.revision = COMMIT

    result = await backend.run("job-pinned", parsed, [], None)

    git_calls = [
        command[command.index(backend._image) + 1 :]
        for command in recorded
        if command[command.index("--entrypoint") + 1] == "git"
    ]
    assert git_calls[:5] == [
        ["init", CONTAINER_REPO],
        [
            "-c",
            f"safe.directory={CONTAINER_REPO}",
            "remote",
            "add",
            "origin",
            "https://github.com/example/project.git",
        ],
        [
            "-c",
            f"safe.directory={CONTAINER_REPO}",
            "fetch",
            "--depth",
            "1",
            "origin",
            COMMIT,
        ],
        [
            "-c",
            f"safe.directory={CONTAINER_REPO}",
            "checkout",
            "--detach",
            "FETCH_HEAD",
        ],
        [
            "-c",
            f"safe.directory={CONTAINER_REPO}",
            "rev-parse",
            "--verify",
            "HEAD^{commit}",
        ],
    ]
    assert not any("--branch" in call for call in git_calls)
    assert result.repository_commit == COMMIT


async def test_a_named_revision_still_uses_shallow_clone_branch(
    backend, recorded, parsed_claim, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(DockerSandboxBackend, "preflight", _noop_preflight)
    parsed = parsed_claim.model_copy(deep=True)
    parsed.execution.revision = "v7.0"

    result = await backend.run("job-tag", parsed, [], None)

    clone = recorded[0]
    image_index = clone.index(backend._image)
    assert clone[image_index + 1 :] == [
        "clone",
        "--depth",
        "1",
        "--branch",
        "v7.0",
        "https://github.com/example/project.git",
        CONTAINER_REPO,
    ]
    assert result.repository_commit == COMMIT


async def _noop_preflight(self) -> None:
    return None


async def test_run_refuses_when_the_daemon_is_unreachable(
    tmp_path, parsed_claim, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stopped daemon is a setup error, never a silent fallback to the host."""
    monkeypatch.setattr("verity.agents.environment.shutil.which", lambda name: None)
    sandbox = DockerSandboxBackend()
    with pytest.raises(SandboxUnavailableError, match="Docker is not installed"):
        await sandbox.run("job-1", parsed_claim, [], None)
