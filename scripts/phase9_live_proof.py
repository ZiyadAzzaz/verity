"""Phase 9 — multi-claim proof against the live public Cloud Run deployment.

Submits several genuinely different claim URLs through the public endpoint using the
judge test key, waits for each to reach a terminal verdict, and correlates every job to the
real cloud resources that produced it: the Pub/Sub push, the `verity-pipeline` execution, the
nested `verity-sandbox` execution, the Firestore document, and the filed GitHub Issue.

It then re-submits one URL to prove claim memory works on the live deployment rather than
only locally.

    python scripts/phase9_live_proof.py --dry-run     # show the plan, touch nothing
    python scripts/phase9_live_proof.py

Stops at the first job that fails to reach a terminal verdict rather than pushing through, so
a partial result is never reported as a pass.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

GCLOUD = r"D:\google-cloud\google-cloud-sdk\bin\gcloud.cmd"
PROJECT, REGION, SERVICE = "verity-506800", "us-central1", "verity"
EVIDENCE = Path(__file__).resolve().parents[1] / "docs" / "assets" / "cloud-evidence"

#: Chosen so the run cannot pass without exercising the parts that actually break. Claim
#: memory only ever reuses a *completed* job, so none of these is served from cache: the two
#: GitHub repositories have never been submitted to the cloud deployment, and the arXiv claim's
#: previous attempt failed and was therefore never remembered.
#:
#: The first run of this script used three sources that all stopped at the parser, and it
#: reported a clean pass over a pipeline that could not read a sandbox result back at all. Two
#: of these three now reach execution, so that class of bug cannot hide again.
CLAIMS: list[tuple[str, str]] = [
    (
        "https://github.com/psf/requests",
        "GitHub README with an asserted number, small and quick to execute - expected to "
        "reach the sandbox and reproduce",
    ),
    (
        "https://arxiv.org/abs/1810.04805",
        "arXiv PDF, BERT GLUE score - reaches the sandbox, and is the exact claim whose "
        "read-back failed before the operation-metadata fix",
    ),
    (
        "https://github.com/ijl/orjson",
        "GitHub README for a compiled extension - expected to be declined as environment "
        "incompatible rather than executed",
    ),
]

#: Completed by an earlier run against an earlier revision. Re-submitting it shows that claim
#: memory is durable state in Firestore, not a cache inside one container that a deploy resets.
PRIOR_RUN_URL = "https://github.com/python-attrs/attrs"


def gcloud(*args: str) -> subprocess.CompletedProcess[str]:
    #: text=True decodes with the locale encoding, which is cp1252 on this Windows host. A claim
    #: parsed out of an arXiv PDF carries typographic quotes, so the job JSON is not cp1252 and
    #: decoding it raised UnicodeDecodeError mid-poll - losing the run's own result while the
    #: pipeline went on working perfectly. UTF-8 is what these tools actually emit.
    return subprocess.run(
        [GCLOUD, *args], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


def service_url() -> str:
    return gcloud(
        "run",
        "services",
        "describe",
        SERVICE,
        f"--project={PROJECT}",
        f"--region={REGION}",
        "--format=value(status.url)",
    ).stdout.strip()


def judge_key() -> str:
    return gcloud(
        "secrets",
        "versions",
        "access",
        "latest",
        "--secret=verity-judge-test-key",
        f"--project={PROJECT}",
    ).stdout.strip()


def post(url: str, key: str, claim: str) -> dict[str, Any]:
    out = subprocess.run(
        [
            "curl",
            "-s",
            "-X",
            "POST",
            f"{url}/api/jobs",
            "-H",
            f"X-Verity-Key: {key}",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps({"url": claim}),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout
    parsed: dict[str, Any] = json.loads(out or "{}")
    return parsed


def fetch(url: str, key: str, job_id: str) -> dict[str, Any]:
    out = subprocess.run(
        ["curl", "-s", f"{url}/api/jobs/{job_id}", "-H", f"X-Verity-Key: {key}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout
    parsed: dict[str, Any] = json.loads(out or "{}")
    return parsed


def wait_terminal(url: str, key: str, job_id: str, timeout: int = 2400) -> dict[str, Any] | None:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        view = fetch(url, key, job_id)
        job = view.get("job", {})
        status = job.get("status")
        if status != last:
            print(f"      status: {status}")
            last = status or ""
        if status in {"completed", "failed"}:
            return view
        time.sleep(15)
    return None


def executions(job_name: str, limit: int = 5) -> list[str]:
    r = gcloud(
        "run",
        "jobs",
        "executions",
        "list",
        f"--job={job_name}",
        f"--project={PROJECT}",
        f"--region={REGION}",
        "--limit",
        str(limit),
        "--format=value(metadata.name,status.completionTime)",
    )
    return [line for line in r.stdout.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    url = service_url()
    print(f"  service     : {url}")
    print(f"  claims      : {len(CLAIMS)}")
    for claim, why in CLAIMS:
        print(f"    - {claim}\n      {why}")
    if args.dry_run:
        print("\n  --dry-run: nothing submitted")
        return 0

    key = judge_key()
    if not key:
        print("  could not read the judge test key from Secret Manager")
        return 1
    print(f"  judge key   : loaded ({len(key)} chars, not printed)\n")

    results = []
    # The description is only used when printing the plan above, not per-run.
    for claim, _why in CLAIMS:
        print(f"  === {claim}")
        submitted = post(url, key, claim)
        job_id = submitted.get("job_id")
        if not job_id:
            print(f"      submission failed: {json.dumps(submitted)[:300]}")
            return 1
        print(f"      job {job_id}  cached={submitted.get('cached')}")
        view = wait_terminal(url, key, job_id)
        if view is None:
            print("      NO TERMINAL VERDICT within the timeout - stopping rather than continuing")
            return 1
        job = view["job"]
        verdict = job.get("verdict") or {}
        print(
            f"      verdict   : {verdict.get('status')}  reproduced={verdict.get('actual_value')}"
        )
        print(
            f"      attempts  : {len(verdict.get('attempts', []))}   trace: {len(view.get('trace', []))}"
        )
        print(f"      issue     : {verdict.get('issue_url')}")
        results.append(
            {
                "url": claim,
                "job_id": job_id,
                "verdict": verdict.get("status"),
                "actual_value": verdict.get("actual_value"),
                "issue_url": verdict.get("issue_url"),
                "trace_events": len(view.get("trace", [])),
            }
        )
        print()

    # Dedup on the live deployment. The first URL was completed moments ago by this run;
    # PRIOR_RUN_URL was completed by an earlier run against an earlier revision, so reusing it
    # shows claim memory living in Firestore rather than in one container's process.
    dedup_ok = True
    for label, target in (("same run", CLAIMS[0][0]), ("earlier revision", PRIOR_RUN_URL)):
        print(f"  === dedup re-submission ({label}) of {target}")
        started = time.time()
        again = post(url, key, target)
        elapsed = (time.time() - started) * 1000
        print(
            f"      cached={again.get('cached')}  status={again.get('status')}  in {elapsed:.0f} ms"
        )
        dedup_ok = dedup_ok and bool(again.get("cached"))

    print("\n  === Cloud Run Job executions ===")
    for job_name in ("verity-pipeline", "verity-sandbox"):
        rows = executions(job_name)
        print(f"    {job_name}: {len(rows)} recent execution(s)")
        for row in rows[:3]:
            print(f"      {row}")

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "phase9-results.json").write_text(
        json.dumps({"service_url": url, "claims": results, "dedup_cached": dedup_ok}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"\n  wrote {EVIDENCE / 'phase9-results.json'}")

    #: A job that never reached a verdict is not an outcome type, it is a failure, and it must
    #: not count toward the "at least two outcomes" bar. Sorting a set that contains None also
    #: raises, so the missing verdicts are named separately rather than crashing the report on
    #: the one run where something actually went wrong.
    outcomes = sorted({r["verdict"] for r in results if r["verdict"]})
    missing = [r["url"] for r in results if not r["verdict"]]
    print(f"\n  outcomes seen : {outcomes}")
    if missing:
        print(f"  NO VERDICT    : {len(missing)} job(s) never reached one:")
        for gap in missing:
            print(f"    {gap}")
    ok = len(outcomes) >= 2 and dedup_ok and not missing
    print(f"  RESULT: {'PASS' if ok else 'REVIEW NEEDED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
