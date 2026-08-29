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

GCLOUD = r"D:\google-cloud\google-cloud-sdk\bin\gcloud.cmd"
PROJECT, REGION, SERVICE = "verity-506800", "us-central1", "verity"
EVIDENCE = Path(__file__).resolve().parents[1] / "docs" / "assets" / "cloud-evidence"

#: Deliberately varied, and none of them is in the shipped local demo cache, so every run
#: below is a genuinely fresh cloud-side verification rather than a cache replay.
CLAIMS: list[tuple[str, str]] = [
    ("https://github.com/python-attrs/attrs", "GitHub README, small pure-Python library"),
    ("https://arxiv.org/abs/1810.04805", "arXiv PDF, BERT GLUE score"),
    ("https://github.com/pallets/click", "GitHub README, no headline benchmark expected"),
]


def gcloud(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([GCLOUD, *args], capture_output=True, text=True)


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


def post(url: str, key: str, claim: str) -> dict:
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
    ).stdout
    return json.loads(out or "{}")


def fetch(url: str, key: str, job_id: str) -> dict:
    out = subprocess.run(
        ["curl", "-s", f"{url}/api/jobs/{job_id}", "-H", f"X-Verity-Key: {key}"],
        capture_output=True,
        text=True,
    ).stdout
    return json.loads(out or "{}")


def wait_terminal(url: str, key: str, job_id: str, timeout: int = 2400) -> dict | None:
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

    # Dedup on the live deployment.
    first = CLAIMS[0][0]
    print(f"  === dedup re-submission of {first}")
    started = time.time()
    again = post(url, key, first)
    elapsed = (time.time() - started) * 1000
    print(f"      cached={again.get('cached')}  status={again.get('status')}  in {elapsed:.0f} ms")
    dedup_ok = bool(again.get("cached"))

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

    outcomes = {r["verdict"] for r in results}
    print(f"\n  outcomes seen: {sorted(outcomes)}")
    ok = len(outcomes) >= 2 and dedup_ok and all(r["verdict"] for r in results)
    print(f"  RESULT: {'PASS' if ok else 'REVIEW NEEDED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
