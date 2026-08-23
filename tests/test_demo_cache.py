"""The shipped demo cache must match what the guide promises.

`docs/assets/demo-cache/verity-demo.db` backs `docs/LOCAL-DEMO.md` and the frontend's example
chips. It drifted twice by absorbing live experimentation, and the second time it shipped a
verdict that contradicted the chip describing it — a judge clicking "no verifiable claim"
would have been shown could_not_verify.

`guard_demo_cache` now prevents the writes. This is the other half: a gate that fails loudly
if the contents stop matching the manifest, rather than waiting for someone to notice while
writing documentation.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
from pathlib import Path

import pytest

from verity.models import JobStatus
from verity.sqlite_store import ALLOW_DEMO_WRITES, SQLiteJobStore, guard_demo_cache

ROOT = Path(__file__).resolve().parents[1]
DEMO_DB = ROOT / "docs" / "assets" / "demo-cache" / "verity-demo.db"
MANIFEST = ROOT / "docs" / "assets" / "demo-cache" / "manifest.json"


def read_manifest() -> list[dict]:
    return list(json.loads(MANIFEST.read_text(encoding="utf-8"))["jobs"])


def read_shipped() -> list[dict]:
    """Open read-only so the gate can never be the thing that mutates the fixture."""

    async def collect() -> list[dict]:
        os.environ[ALLOW_DEMO_WRITES] = "1"
        store = SQLiteJobStore(DEMO_DB)
        try:
            connection = sqlite3.connect(DEMO_DB)
            rows = []
            for (job_id,) in connection.execute("select id from jobs"):
                job = await store.get_job(job_id)
                assert job is not None and job.verdict is not None
                rows.append(
                    {
                        "url": str(job.source_url).rstrip("/"),
                        "verdict": job.verdict.status.value,
                        "metric": job.verdict.claim.metric,
                        "actual_value": job.verdict.actual_value,
                        "status": job.status,
                    }
                )
            connection.close()
            return rows
        finally:
            store.close()
            os.environ.pop(ALLOW_DEMO_WRITES, None)

    return asyncio.run(collect())


def test_the_demo_cache_matches_its_manifest() -> None:
    expected = {entry["url"]: entry for entry in read_manifest()}
    actual = {entry["url"]: entry for entry in read_shipped()}

    extra = sorted(set(actual) - set(expected))
    missing = sorted(set(expected) - set(actual))
    assert not extra, (
        f"the shipped demo cache has drifted - unexpected jobs: {extra}. "
        "Something wrote to it outside scripts/rebuild_demo_cache.py."
    )
    assert not missing, f"the shipped demo cache is missing curated jobs: {missing}"

    for url, want in expected.items():
        got = actual[url]
        assert got["verdict"] == want["verdict"], f"{url}: verdict changed"
        assert got["metric"] == want["metric"], f"{url}: claim changed"
        assert got["actual_value"] == want["actual_value"], f"{url}: reproduced value changed"


def test_every_shipped_job_is_complete() -> None:
    """A job with no verdict is scratch state, not a demo fixture."""
    for entry in read_shipped():
        assert entry["status"] == JobStatus.COMPLETED, f"{entry['url']} is {entry['status']}"


def test_the_demo_covers_more_than_one_outcome() -> None:
    """A demo showing only failures undersells it; one showing only successes is dishonest."""
    outcomes = {entry["verdict"] for entry in read_shipped()}
    assert "verified" in outcomes, "the demo must include a claim that reproduces"
    assert "could_not_verify" in outcomes, "the demo must include an honest failure"
    assert len(outcomes) >= 3, f"only {len(outcomes)} outcome(s) shown: {sorted(outcomes)}"


class TestWriteGuard:
    """The mechanism that stops the drift, rather than a habit of remembering."""

    def test_opening_the_shipped_cache_for_writing_is_refused(self) -> None:
        os.environ.pop(ALLOW_DEMO_WRITES, None)
        with pytest.raises(RuntimeError, match="Refusing to open the shipped demo cache"):
            SQLiteJobStore(DEMO_DB)

    def test_the_explicit_opt_in_is_honoured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ALLOW_DEMO_WRITES, "1")
        store = SQLiteJobStore(DEMO_DB)
        store.close()

    def test_any_other_path_is_unaffected(self, tmp_path: Path) -> None:
        guard_demo_cache(tmp_path / "verity.db")
        guard_demo_cache(tmp_path / "verity-demo.db")  # right name, wrong directory
        store = SQLiteJobStore(tmp_path / "scratch.db")
        store.close()
