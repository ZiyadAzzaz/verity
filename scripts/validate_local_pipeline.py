"""The local end-to-end gate: real claim URLs, real Gemini, real containers, no GCP.

Runs the full Parser -> Environment -> Debug -> Reporter pipeline against the sources in
``tests/data/local_claim_urls.json`` using the local adapters only: SQLite, the asyncio
queue, the Docker sandbox, and a Google AI Studio key.

What counts as passing is deliberately *not* "everything verified". Most public claims do
not reproduce on a laptop, and Verity's job is to say so. A run passes when every job
reaches a verdict with evidence behind it, and no job reports a reproduced number it did
not actually observe.

    python scripts/validate_local_pipeline.py                 # all URLs
    python scripts/validate_local_pipeline.py --limit 3       # first three
    python scripts/validate_local_pipeline.py --url https://github.com/psf/requests

Requires GEMINI_API_KEY and a running Docker daemon.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verity.config import Settings
from verity.container import build_container
from verity.models import JobStatus, VerdictStatus
from verity.telemetry import configure_telemetry

DATA = Path(__file__).resolve().parents[1] / "tests" / "data" / "local_claim_urls.json"


def load_urls() -> list[dict[str, str]]:
    return list(json.loads(DATA.read_text(encoding="utf-8"))["urls"])


async def run(urls: list[str], *, database: str, timeout: float) -> int:
    configure_telemetry()
    settings = Settings(env="local", sqlite_path=database)
    container = build_container(settings)
    await container.preflight()
    await container.startup()

    rows: list[tuple[str, str, str, float]] = []
    failures: list[str] = []
    try:
        for url in urls:
            print(f"\n=== {url}", flush=True)
            started = time.monotonic()
            response = await container.orchestrator.submit(url)
            if response.cached:
                print("  cached verdict returned instantly")

            deadline = time.monotonic() + timeout
            job = await container.store.get_job(response.job_id)
            while job is not None and job.status not in {
                JobStatus.COMPLETED,
                JobStatus.FAILED,
            }:
                if time.monotonic() > deadline:
                    break
                await asyncio.sleep(2)
                job = await container.store.get_job(response.job_id)

            elapsed = time.monotonic() - started
            if job is None:
                failures.append(f"{url}: job record disappeared")
                continue
            if job.status not in {JobStatus.COMPLETED, JobStatus.FAILED}:
                failures.append(f"{url}: still {job.status.value} after {timeout:.0f}s")
                rows.append((url, job.status.value, "-", elapsed))
                continue

            verdict = job.verdict
            if verdict is None:
                failures.append(f"{url}: finished as {job.status.value} without a verdict")
                print(f"  FAILED: {job.error}")
                rows.append((url, job.status.value, "no verdict", elapsed))
                continue

            # The honesty invariant: a number may only be reported when a run produced it.
            if verdict.status in {VerdictStatus.VERIFIED, VerdictStatus.CONTRADICTED} and (
                verdict.actual_value is None
            ):
                failures.append(f"{url}: {verdict.status.value} without a reproduced value")
            if verdict.status == VerdictStatus.COULD_NOT_VERIFY and (
                verdict.actual_value is not None
            ):
                failures.append(f"{url}: could_not_verify but still reported a value")

            trace = await container.store.get_trace(job.id)
            print(
                f"  claim      : {verdict.claim.metric} = {verdict.claim.value:g}"
                f"{verdict.claim.unit} on {verdict.claim.dataset}"
            )
            print(f"  verdict    : {verdict.status.value} ({verdict.confidence.value})")
            print(f"  reproduced : {verdict.actual_value}")
            print(f"  attempts   : {len(verdict.attempts)}")
            print(f"  trace      : {len(trace)} events in {elapsed:.1f}s")
            print(f"  summary    : {verdict.summary[:200]}")
            rows.append((url, verdict.status.value, str(verdict.actual_value), elapsed))

        # Dedup check: the first URL again must come back without re-running anything.
        if urls:
            started = time.monotonic()
            repeat = await container.orchestrator.submit(urls[0])
            elapsed = time.monotonic() - started
            print(f"\n=== dedup re-submission of {urls[0]}")
            print(f"  cached={repeat.cached} in {elapsed:.3f}s")
            if not repeat.cached:
                failures.append("dedup: the second submission was not served from claim memory")
            elif elapsed > 2.0:
                failures.append(f"dedup: cached response took {elapsed:.1f}s")
    finally:
        await container.shutdown()

    print("\n" + "-" * 88)
    for url, status, actual, elapsed in rows:
        print(f"{status:<18} {actual:<12} {elapsed:>7.1f}s  {url}")
    print("-" * 88)

    if failures:
        print(f"\n{len(failures)} problem(s):")
        for problem in failures:
            print(f"  - {problem}")
        return 1
    print(f"\nAll {len(rows)} claims reached an evidence-backed verdict locally.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", help="run only this URL (repeatable)")
    parser.add_argument("--limit", type=int, help="run only the first N catalogue URLs")
    parser.add_argument("--database", default="verity-local-validation.db")
    parser.add_argument("--timeout", type=float, default=1800, help="per-job seconds")
    args = parser.parse_args()

    urls = args.url or [entry["url"] for entry in load_urls()]
    if args.limit:
        urls = urls[: args.limit]
    raise SystemExit(asyncio.run(run(urls, database=args.database, timeout=args.timeout)))


if __name__ == "__main__":
    main()
