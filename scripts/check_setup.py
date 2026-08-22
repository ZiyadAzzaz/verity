"""One command that answers: is this machine ready to run Verity locally?

    python scripts/check_setup.py

Checks the Python environment, the .env key, and the Docker daemon, then prints a
short report that is safe to share — the API key is never printed, only whether one is
present and how long it is.

Every Docker call is hard-timeboxed, so this script cannot hang the way a bare
`docker info` does when Docker Desktop is sitting on its onboarding screen.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OK = "  [ OK ]"
NO = "  [FAIL]"
WARN = "  [warn]"


def run(command: list[str], timeout: int) -> tuple[bool, str]:
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    except OSError as exc:
        return False, str(exc)
    if done.returncode != 0:
        return False, (done.stderr or done.stdout).strip()[:300]
    return True, done.stdout.strip()


def check_python() -> bool:
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    prefix = Path(sys.prefix)
    label = prefix.name if prefix.parent.name == "envs" else str(prefix)
    if sys.version_info[:2] != (3, 11):
        print(f"{NO} Python {version} in '{label}' - Verity needs 3.11")
        print("         Run: conda activate agent-dev")
        return False
    print(f"{OK} Python {version} in '{label}'")
    if prefix.parent.name != "envs" and not (prefix / "pyvenv.cfg").is_file():
        print(f"{WARN} this is not an isolated environment - expected agent-dev or .venv")
    return True


def check_dependencies() -> bool:
    """Runtime *and* dev tooling. A partial install is the failure mode to catch here."""
    runtime = {"fastapi": "fastapi", "pydantic": "pydantic", "google.adk": "google-adk"}
    tooling = {"ruff": "ruff", "mypy": "mypy", "pytest": "pytest"}
    missing: list[str] = []
    for module, package in {**runtime, **tooling}.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    if missing:
        print(f"{NO} packages missing: {', '.join(missing)}")
        print("         An interrupted download leaves the environment half-installed.")
        print("         Repair with: python -m pip install --retries 10 -r requirements.txt")
        return False
    print(f"{OK} dependencies and dev tooling installed")
    return True


def check_key() -> bool:
    """Report only whether a key exists and its length. Never the value."""
    from verity.config import Settings

    settings = Settings()
    if not settings.gemini_api_key:
        print(f"{NO} GEMINI_API_KEY is empty")
        print(f"         Add it to {ROOT / '.env'} - free key: https://aistudio.google.com/")
        return False
    length = len(settings.gemini_api_key.get_secret_value())
    print(f"{OK} GEMINI_API_KEY is set ({length} characters)")
    print(
        f"{OK} profile: env={settings.env} store={settings.store} "
        f"queue={settings.messaging} sandbox={settings.sandbox} model={settings.llm}"
    )
    return True


def check_docker() -> bool:
    from verity.config import Settings

    if shutil.which("docker") is None:
        print(f"{NO} the docker CLI is not on PATH")
        return False
    alive, detail = run(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=45)
    if not alive:
        print(f"{NO} the Docker daemon is not responding ({detail or 'no output'})")
        print("         Open the Docker Desktop window and finish its setup screen")
        print("         (accept the licence / sign in), then wait for 'Engine running'.")
        return False
    print(f"{OK} Docker daemon {detail}")

    image = Settings().sandbox_image
    present, _ = run(["docker", "image", "inspect", image], timeout=60)
    if present:
        print(f"{OK} sandbox image {image} is built")
    else:
        print(f"{WARN} sandbox image {image} is not built yet")
        print("         It builds automatically on the first job (slow, several minutes).")
        print(f"         To pre-build: docker build -f Dockerfile.runner -t {image} .")
    return True


def main() -> int:
    print("\nVerity local setup check\n" + "-" * 60)
    environment = check_python() and check_dependencies()
    key = check_key() if environment else False
    docker = check_docker() if environment else False
    print("-" * 60)

    if environment and key and docker:
        print("READY - everything the local pipeline needs is in place.\n")
        return 0

    print("NOT READY. Outstanding:")
    if not environment:
        print("  - Python 3.11 environment (scripts/bootstrap.ps1)")
    if environment and not key:
        print("  - GEMINI_API_KEY in .env")
    if environment and not docker:
        print("  - a responding Docker daemon")
    print("\nSee docs/HANDOVER.md for setup details.\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
