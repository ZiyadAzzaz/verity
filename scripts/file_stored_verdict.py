"""File a GitHub Issue for a verdict that was already produced by a real pipeline run.

The Reporter Agent is deterministic Python with no model call, so replaying a stored verdict
through it costs no Gemini quota. That makes this the way to prove the autonomous deliverable
end to end without re-running an expensive verification.

    python scripts/file_stored_verdict.py --database E:\\wsl\\verity-gate4.db --list
    python scripts/file_stored_verdict.py --database E:\\wsl\\verity-gate4.db --job <id>

Requires VERITY_GITHUB_TOKEN and VERITY_REPORT_REPO. The token is read from the environment
or .env and is never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verity.config import get_settings
from verity.github import GitHubIssuePublisher, render_issue
from verity.models import JobStatus
from verity.sqlite_store import SQLiteJobStore


async def run(database: str, job_id: str | None, list_only: bool) -> int:
    settings = get_settings()
    store = SQLiteJobStore(database)
    try:
        connection = sqlite3.connect(database)
        ids = [row[0] for row in connection.execute("select id from jobs").fetchall()]
        connection.close()

        completed = []
        for candidate in ids:
            job = await store.get_job(candidate)
            if job is not None and job.status == JobStatus.COMPLETED and job.verdict is not None:
                completed.append(job)

        if list_only or job_id is None:
            print(f"{len(completed)} completed job(s) with a verdict in {database}:\n")
            for job in completed:
                verdict = job.verdict
                assert verdict is not None
                print(f"  {job.id}")
                print(f"    {job.source_url}")
                print(
                    f"    {verdict.status.value} - {verdict.claim.metric} = "
                    f"{verdict.claim.value:g}{verdict.claim.unit} on {verdict.claim.dataset}"
                )
                print(
                    f"    reproduced: {verdict.actual_value}   attempts: {len(verdict.attempts)}\n"
                )
            if list_only:
                return 0
            print("Pass --job <id> to file one of these as a real GitHub Issue.")
            return 1

        job = await store.get_job(job_id)
        if job is None or job.verdict is None:
            print(f"job {job_id} has no stored verdict")
            return 1
        if not settings.github_token:
            print("VERITY_GITHUB_TOKEN is not set - cannot file a real Issue.")
            return 1
        if not settings.report_repo:
            print("VERITY_REPORT_REPO is not set - no fallback target for the Issue.")
            return 1

        if job.parsed_claim is None:
            print(f"job {job_id} has no stored parsed claim")
            return 1

        publisher = GitHubIssuePublisher(
            settings.github_token.get_secret_value(),
            fallback_repo=settings.report_repo,
        )
        verdict = job.verdict

        print(f"filing verdict for {job.source_url}")
        print(
            f"  {verdict.status.value} - {verdict.claim.metric} = "
            f"{verdict.claim.value:g}{verdict.claim.unit} on {verdict.claim.dataset}"
        )
        print(f"  reproduced: {verdict.actual_value}   attempts: {len(verdict.attempts)}")
        print(f"  fallback repository: {settings.report_repo}")

        # Exactly the path ReporterAgent.run takes after synthesising a verdict: the same
        # render_issue call and the same publisher. Nothing about the issue body is
        # hand-rolled here, so what lands is what the pipeline itself would file.
        title, body = render_issue(verdict, job.parsed_claim, job.id)
        issue_url = await publisher.publish(job.parsed_claim, title, body)
        if issue_url:
            print(f"\nIssue filed: {issue_url}")
            return 0
        print("\nno issue URL returned")
        return 1
    finally:
        store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--job", help="job id to file")
    parser.add_argument("--list", action="store_true", dest="list_only")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.database, args.job, args.list_only)))


if __name__ == "__main__":
    main()
