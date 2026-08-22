"""Submit seven varied real URLs, wait for terminal states, and verify dedup."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

import httpx


async def wait_for_job(client: httpx.AsyncClient, job_id: str, timeout: int) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = await client.get(f"/api/jobs/{job_id}")
        response.raise_for_status()
        view = response.json()
        if view["job"]["status"] in {"completed", "failed"}:
            return view
        await asyncio.sleep(5)
    raise TimeoutError(f"job {job_id} did not finish within {timeout}s")


async def main(base_url: str, timeout: int) -> None:
    api_key = os.environ.get("VERITY_API_KEY")
    if not api_key:
        raise SystemExit("Set VERITY_API_KEY for the deployed service.")
    urls = json.loads(Path("tests/data/deployed_claim_urls.json").read_text(encoding="utf-8"))
    terminal: list[dict] = []
    async with httpx.AsyncClient(
        base_url=base_url.rstrip("/"),
        headers={"X-Verity-Key": api_key},
        timeout=60,
    ) as client:
        for url in urls:
            response = await client.post("/api/jobs", json={"url": url})
            response.raise_for_status()
            submitted = response.json()
            view = await wait_for_job(client, submitted["job_id"], timeout)
            terminal.append(
                {
                    "url": url,
                    "job_id": submitted["job_id"],
                    "status": view["job"]["status"],
                    "verdict": (view["job"].get("verdict") or {}).get("status"),
                    "issue_url": (view["job"].get("verdict") or {}).get("issue_url"),
                }
            )
            print(json.dumps(terminal[-1], indent=2))

        started = time.monotonic()
        duplicate = await client.post("/api/jobs", json={"url": urls[0]})
        duplicate.raise_for_status()
        elapsed = time.monotonic() - started
        cached = duplicate.json()
        if not cached["cached"] or elapsed >= 2:
            raise AssertionError(
                f"dedup was not instant: cached={cached['cached']} elapsed={elapsed}"
            )
    if any(item["status"] != "completed" for item in terminal):
        raise SystemExit(
            "One or more deployed verification jobs failed before producing a verdict."
        )
    if any(not item["issue_url"] for item in terminal):
        raise SystemExit("One or more deployed jobs did not file a GitHub Issue.")
    print(f"Validated {len(terminal)} deployed real claims plus instant dedup.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    parser.add_argument("--timeout", type=int, default=3600)
    args = parser.parse_args()
    asyncio.run(main(args.base_url, args.timeout))
