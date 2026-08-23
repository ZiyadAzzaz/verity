"""Rebuild the shipped demo cache from real runs, deliberately.

`docs/assets/demo-cache/verity-demo.db` backs `docs/LOCAL-DEMO.md`, so what is in it is a
documented promise. It absorbed live experimentation twice before `guard_demo_cache` existed;
this script is the only sanctioned way to change it, and it is the only caller that sets
``VERITY_ALLOW_DEMO_CACHE_WRITES``.

    python scripts/rebuild_demo_cache.py --dry-run    # show what would ship
    python scripts/rebuild_demo_cache.py              # rebuild it

Each entry names the database the verdict actually came from. Nothing is synthesised: every
job here was produced by a real pipeline run against the real source.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["VERITY_ALLOW_DEMO_CACHE_WRITES"] = "1"

from verity.sqlite_store import SQLiteJobStore  # noqa: E402

DEMO_DB = ROOT / "docs" / "assets" / "demo-cache" / "verity-demo.db"
MANIFEST = ROOT / "docs" / "assets" / "demo-cache" / "manifest.json"

#: url -> the database holding the run that produced its verdict.
SOURCES: dict[str, str] = {
    "https://arxiv.org/abs/1512.03385": "E:/wsl/verity-gate4.db",
    "https://arxiv.org/abs/1706.03762": "E:/wsl/verity-gate4.db",
    "https://github.com/psf/requests": "E:/wsl/verity-gate4.db",
    "https://github.com/ZiyadAzzaz/Stroke-Data-Analysis": "E:/wsl/verity-live.db",
    "https://github.com/ijl/orjson": "E:/wsl/verity-orjson.db",
}

#: Issues filed for these verdicts, so the UI can link to the artifact.
ISSUE_URLS: dict[str, str] = {
    "https://arxiv.org/abs/1512.03385": "https://github.com/ZiyadAzzaz/verity-reports/issues/1",
    "https://github.com/ijl/orjson": "https://github.com/ZiyadAzzaz/verity-reports/issues/4",
}


async def collect(url: str, source_db: str):
    """Find the completed job for this URL in the database that produced it."""
    if not Path(source_db).is_file():
        return None
    connection = sqlite3.connect(source_db)
    store = SQLiteJobStore(source_db)
    try:
        found = None
        for (job_id,) in connection.execute("select id from jobs"):
            job = await store.get_job(job_id)
            if job and str(job.source_url).rstrip("/") == url and job.verdict is not None:
                found = (job, await store.get_trace(job_id))
        return found
    finally:
        store.close()
        connection.close()


async def run(dry_run: bool) -> int:
    collected = []
    for url, source_db in SOURCES.items():
        item = await collect(url, source_db)
        if item is None:
            print(f"  MISSING  {url}  (not found in {source_db})")
            return 1
        job, trace = item
        verdict = job.verdict
        assert verdict is not None
        collected.append((url, job, trace))
        print(
            f"  {verdict.status.value:26} {verdict.claim.metric[:26]:26} "
            f"actual={verdict.actual_value!s:6} {url}"
        )

    outcomes = sorted({job.verdict.status.value for _u, job, _t in collected})
    print(f"\n  {len(collected)} jobs covering {len(outcomes)} outcomes: {', '.join(outcomes)}")

    if dry_run:
        print("\n  --dry-run: nothing written")
        return 0

    if DEMO_DB.exists():
        DEMO_DB.unlink()
    for suffix in ("-wal", "-shm"):
        sidecar = DEMO_DB.with_name(DEMO_DB.name + suffix)
        if sidecar.exists():
            sidecar.unlink()

    destination = SQLiteJobStore(DEMO_DB)
    try:
        for url, job, trace in collected:
            fresh, _created = await destination.create_or_get(url)
            await destination.update_job(fresh.id, parsed_claim=job.parsed_claim)
            for event in trace:
                await destination.append_trace(
                    fresh.id, agent=event.agent, action=event.action, detail=event.detail
                )
            verdict = job.verdict
            assert verdict is not None
            if url in ISSUE_URLS:
                verdict = verdict.model_copy(update={"issue_url": ISSUE_URLS[url]})
            await destination.complete_job(fresh.id, verdict)
    finally:
        destination.close()

    MANIFEST.write_text(
        json.dumps(
            {
                "comment": (
                    "The curated contents of verity-demo.db. tests/test_demo_cache.py fails if "
                    "the shipped database drifts from this. Regenerate both with "
                    "scripts/rebuild_demo_cache.py."
                ),
                "jobs": sorted(
                    (
                        {
                            "url": url,
                            "verdict": job.verdict.status.value,  # type: ignore[union-attr]
                            "metric": job.verdict.claim.metric,  # type: ignore[union-attr]
                            "actual_value": job.verdict.actual_value,  # type: ignore[union-attr]
                        }
                        for url, job, _t in collected
                        if job.verdict
                    ),
                    key=lambda entry: str(entry["url"]),
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\n  wrote {DEMO_DB.relative_to(ROOT)} and {MANIFEST.relative_to(ROOT)}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.dry_run)))


if __name__ == "__main__":
    main()
