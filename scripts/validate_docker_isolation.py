"""Prove the sandbox boundary holds, on this machine, right now.

Verity clones and runs arbitrary third-party code from GitHub. This script is the
standalone evidence that such code cannot touch the host: it starts real containers
through the same :class:`DockerSandboxBackend` the Environment Agent uses and tries, one
by one, to escape.

    python scripts/validate_docker_isolation.py

Exit code 0 means every escape attempt failed, which is the desired result.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verity.agents.environment import CONTAINER_WORKSPACE, DockerSandboxBackend
from verity.interfaces import SandboxUnavailableError

READ_HOST = """
import os, sys
targets = [{host!r}, '/work/../host-secret.txt', '/host_mnt', '/mnt/host']
found = [t for t in targets if os.path.exists(t)]
print('reachable:', found)
sys.exit(1 if found else 0)
"""

WRITE_OUTSIDE = """
import sys
for target in ('/etc/verity-probe', '/usr/verity-probe', '/verity-probe', '/home/verity-probe'):
    try:
        open(target, 'w').write('x')
    except OSError:
        continue
    print('WROTE', target)
    sys.exit(1)
sys.exit(0)
"""

NO_NETWORK = """
import socket, sys
for host, port in (('8.8.8.8', 53), ('pypi.org', 443)):
    try:
        socket.create_connection((host, port), timeout=5)
    except OSError:
        continue
    print('reached', host)
    sys.exit(1)
sys.exit(0)
"""

HAS_NETWORK = """
import socket, sys
try:
    socket.create_connection(('pypi.org', 443), timeout=20)
except OSError as exc:
    print(exc)
    sys.exit(1)
sys.exit(0)
"""

IDENTITY = """
import os, sys
caps = dict(line.split(':', 1) for line in open('/proc/self/status') if ':' in line)
effective = int(caps.get('CapEff', '0').strip(), 16)
print('uid', os.geteuid(), 'CapEff', hex(effective),
      'NoNewPrivs', caps.get('NoNewPrivs', '?').strip())
sys.exit(0 if os.geteuid() != 0 and effective == 0 else 1)
"""

DOCKER_SOCKET = """
import os, sys
sys.exit(1 if os.path.exists('/var/run/docker.sock') else 0)
"""

FORK_BOMB_LIMIT = """
import os, sys
children = 0
try:
    while children < 5000:
        if os.fork() == 0:
            os._exit(0)
        children += 1
except OSError:
    print('pid limit reached after', children)
    sys.exit(0)
print('no pid limit; forked', children)
sys.exit(1)
"""


def main() -> int:
    backend = DockerSandboxBackend(dockerfile=Path("Dockerfile.runner"))
    try:
        backend._preflight_sync()
    except SandboxUnavailableError as exc:
        print(f"Docker is not usable: {exc}")
        return 2

    with tempfile.TemporaryDirectory(prefix="verity-isolation-") as temp:
        parent = Path(temp)
        secret = parent / "host-secret.txt"
        secret.write_text("do-not-leak", encoding="utf-8")
        workspace = parent / "workspace"
        workspace.mkdir()

        checks: list[tuple[str, str, str]] = [
            (
                "host files outside the workspace are unreachable",
                READ_HOST.format(host=str(secret.resolve()).replace("\\", "/")),
                "none",
            ),
            ("the container filesystem is read-only outside /work", WRITE_OUTSIDE, "none"),
            ("the evaluation phase has no network", NO_NETWORK, "none"),
            ("the install phase can still reach PyPI", HAS_NETWORK, "bridge"),
            ("the sandbox is non-root with no capabilities", IDENTITY, "none"),
            ("the Docker socket is not exposed", DOCKER_SOCKET, "none"),
            ("process count is capped", FORK_BOMB_LIMIT, "none"),
        ]

        failures = 0
        for description, code, network in checks:
            try:
                exit_code, stdout, stderr = backend._docker_run(
                    workspace,
                    ["python", "-c", code],
                    network=network,
                    workdir=CONTAINER_WORKSPACE,
                    timeout=180,
                )
            except subprocess.TimeoutExpired:
                exit_code, stdout, stderr = -1, "", "timed out"
            status = "PASS" if exit_code == 0 else "FAIL"
            if exit_code != 0:
                failures += 1
            print(f"[{status}] {description}")
            detail = (stdout.strip() or stderr.strip())[:400]
            if detail:
                print(f"        {detail}")

        # The workspace itself must remain usable — isolation, not paralysis.
        exit_code, _stdout, stderr = backend._docker_run(
            workspace,
            ["python", "-c", "open('/work/proof.txt','w').write('ok')"],
            network="none",
            workdir=CONTAINER_WORKSPACE,
            timeout=180,
        )
        wrote = (workspace / "proof.txt").is_file()
        print(f"[{'PASS' if exit_code == 0 and wrote else 'FAIL'}] the workspace is writable")
        if exit_code != 0 or not wrote:
            failures += 1
            print(f"        {stderr[:400]}")

    if failures:
        print(f"\n{failures} isolation check(s) failed. Do not run untrusted claims.")
        return 1
    print("\nEvery escape attempt failed. The sandbox boundary holds on this machine.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
