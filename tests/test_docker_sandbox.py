"""Docker isolation checks.

These run real containers, so they are marked ``docker`` and skipped when no daemon is
reachable. They are the evidence behind the claim that Verity does not execute untrusted
third-party code on the host: each one tries to break out and asserts that it cannot.

Run them explicitly with:  pytest -m docker
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from verity.agents.environment import CONTAINER_WORKSPACE, DockerSandboxBackend
from verity.interfaces import SandboxUnavailableError

pytestmark = pytest.mark.docker


@pytest.fixture(scope="module")
def backend() -> DockerSandboxBackend:
    sandbox = DockerSandboxBackend(dockerfile=Path("Dockerfile.runner"))
    try:
        sandbox._preflight_sync()
    except SandboxUnavailableError as exc:
        pytest.skip(f"Docker is not available: {exc}")
    return sandbox


def probe(backend: DockerSandboxBackend, workspace: Path, code: str, *, network: str = "none"):
    return backend._docker_run(
        workspace,
        ["python", "-c", code],
        network=network,
        workdir=CONTAINER_WORKSPACE,
        timeout=180,
    )


def test_workspace_is_readable_and_writable(backend, tmp_path: Path) -> None:
    (tmp_path / "input.txt").write_text("hello", encoding="utf-8")
    code, _stdout, stderr = probe(
        backend,
        tmp_path,
        "open('/work/output.txt','w').write(open('/work/input.txt').read().upper())",
    )
    assert code == 0, stderr
    assert (tmp_path / "output.txt").read_text(encoding="utf-8") == "HELLO"


def test_host_files_outside_the_workspace_are_invisible(backend, tmp_path: Path) -> None:
    """The bind mount is one fresh directory — its own parent is already out of reach."""
    secret = tmp_path / "host-secret.txt"
    secret.write_text("do-not-leak", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    posix_secret = str(secret.resolve()).replace("\\", "/")
    code, stdout, stderr = probe(
        backend,
        workspace,
        "import os,sys;"
        f"p={posix_secret!r};"
        "sys.exit(0 if not os.path.exists(p) and not os.path.exists('/work/../host-secret.txt')"
        " else 1)",
    )
    assert code == 0, f"host file was reachable from the sandbox\n{stdout}\n{stderr}"


def test_container_filesystem_outside_the_workspace_is_read_only(backend, tmp_path: Path) -> None:
    code, stdout, stderr = probe(
        backend,
        tmp_path,
        "import sys\n"
        "for target in ('/etc/verity-probe', '/usr/verity-probe', '/verity-probe'):\n"
        "    try:\n"
        "        open(target, 'w').write('x')\n"
        "    except OSError:\n"
        "        continue\n"
        "    print('WROTE', target)\n"
        "    sys.exit(1)\n"
        "sys.exit(0)\n",
    )
    assert code == 0, f"the sandbox root filesystem is writable\n{stdout}\n{stderr}"


def test_the_evaluation_phase_has_no_network(backend, tmp_path: Path) -> None:
    code, stdout, stderr = probe(
        backend,
        tmp_path,
        "import socket,sys\n"
        "try:\n"
        "    socket.create_connection(('8.8.8.8', 53), timeout=5)\n"
        "except OSError:\n"
        "    sys.exit(0)\n"
        "sys.exit(1)\n",
        network="none",
    )
    assert code == 0, f"the benchmark phase reached the network\n{stdout}\n{stderr}"


def test_the_install_phase_does_have_network(backend, tmp_path: Path) -> None:
    """Declared dependencies must still be installable — isolation, not a dead end."""
    code, stdout, stderr = probe(
        backend,
        tmp_path,
        "import socket,sys\n"
        "try:\n"
        "    socket.create_connection(('pypi.org', 443), timeout=15)\n"
        "except OSError as exc:\n"
        "    print(exc)\n"
        "    sys.exit(1)\n"
        "sys.exit(0)\n",
        network="bridge",
    )
    assert code == 0, f"the install phase could not reach PyPI\n{stdout}\n{stderr}"


def test_the_sandbox_does_not_run_as_root(backend, tmp_path: Path) -> None:
    code, stdout, stderr = probe(backend, tmp_path, "import os;print(os.geteuid())")
    assert code == 0, stderr
    assert stdout.strip() != "0", "the sandbox container is running as root"


def test_privilege_escalation_is_blocked(backend, tmp_path: Path) -> None:
    """--cap-drop ALL plus no-new-privileges: nothing can gain capabilities."""
    code, stdout, stderr = probe(
        backend,
        tmp_path,
        "import sys\n"
        "caps = dict(\n"
        "    line.split(':', 1) for line in open('/proc/self/status')\n"
        "    if ':' in line\n"
        ")\n"
        "effective = caps.get('CapEff', '0').strip()\n"
        "print('CapEff', effective, 'NoNewPrivs', caps.get('NoNewPrivs', '?').strip())\n"
        "sys.exit(0 if int(effective, 16) == 0 else 1)\n",
    )
    assert code == 0, f"the sandbox retained Linux capabilities\n{stdout}\n{stderr}"
    assert "NoNewPrivs 1" in stdout


def test_no_docker_socket_is_exposed(backend, tmp_path: Path) -> None:
    """A reachable /var/run/docker.sock would make every other limit meaningless."""
    code, _stdout, _stderr = probe(
        backend,
        tmp_path,
        "import os,sys;sys.exit(1 if os.path.exists('/var/run/docker.sock') else 0)",
    )
    assert code == 0, "the Docker socket is visible inside the sandbox"


def test_a_hung_container_is_killed_and_removed(backend, tmp_path: Path) -> None:
    with pytest.raises(subprocess.TimeoutExpired):
        backend._docker_run(
            tmp_path,
            ["python", "-c", "import time;time.sleep(600)"],
            network="none",
            workdir=CONTAINER_WORKSPACE,
            timeout=5,
        )
    survivors = subprocess.run(
        ["docker", "ps", "--filter", "name=verity-", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert survivors.stdout.strip() == "", "a timed-out sandbox container was left running"
