from __future__ import annotations

import subprocess
import sys

from verity import worker


def test_worker_main_passes_the_supplied_job_id_to_run(monkeypatch) -> None:
    observed: list[str] = []

    async def fake_run(job_id: str) -> None:
        observed.append(job_id)

    monkeypatch.setattr(worker, "_run", fake_run)
    monkeypatch.setattr(sys, "argv", ["verity-worker", "job-123"])

    worker.main()

    assert observed == ["job-123"]


def test_worker_module_help_proves_the_main_guard_executes() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "verity.worker", "--help"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0
    assert "Process one queued Verity job" in completed.stdout
    assert "job_id" in completed.stdout
