"""Minimal GitHub Issues REST client with a controlled fallback report repository."""

from __future__ import annotations

import re
from typing import Protocol
from urllib.parse import urlsplit

import httpx

from verity.models import ParsedClaim, Verdict, VerdictStatus

REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class IssuePublisher(Protocol):
    async def publish(self, parsed_claim: ParsedClaim, title: str, body: str) -> str | None: ...


class NoopIssuePublisher:
    async def publish(self, parsed_claim: ParsedClaim, title: str, body: str) -> str | None:
        return None


class GitHubIssuePublisher:
    def __init__(self, token: str, *, fallback_repo: str | None = None) -> None:
        if fallback_repo and not REPO_NAME.fullmatch(fallback_repo):
            raise ValueError("VERITY_REPORT_REPO must use owner/repository format")
        self._token = token
        self._fallback = fallback_repo

    @staticmethod
    def _source_repo(parsed_claim: ParsedClaim) -> str | None:
        url = parsed_claim.execution.repository_url
        if url is None or urlsplit(str(url)).hostname != "github.com":
            return None
        parts = [part for part in urlsplit(str(url)).path.split("/") if part]
        if len(parts) < 2:
            return None
        return f"{parts[0]}/{parts[1].removesuffix('.git')}"

    async def publish(self, parsed_claim: ParsedClaim, title: str, body: str) -> str | None:
        targets: list[str] = []
        source_repo = self._source_repo(parsed_claim)
        if source_repo:
            targets.append(source_repo)
        if self._fallback and self._fallback not in targets:
            targets.append(self._fallback)
        if not targets:
            raise RuntimeError("no GitHub repository is available for the verdict issue")

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Verity/0.1",
        }
        failures: list[str] = []
        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            for repo in targets:
                response = await client.post(
                    f"https://api.github.com/repos/{repo}/issues",
                    json={"title": title[:256], "body": body[:65_000], "labels": ["verity-report"]},
                )
                if response.status_code == 422:
                    # A target repository may not define the optional label.
                    response = await client.post(
                        f"https://api.github.com/repos/{repo}/issues",
                        json={"title": title[:256], "body": body[:65_000]},
                    )
                if response.is_success:
                    return str(response.json()["html_url"])
                failures.append(f"{repo}: HTTP {response.status_code} {response.text[:500]}")
        raise RuntimeError("GitHub issue filing failed; " + "; ".join(failures))


def render_issue(verdict: Verdict, parsed_claim: ParsedClaim, job_id: str) -> tuple[str, str]:
    claim = verdict.claim
    title = f"[Verity: {verdict.status.value}] {claim.metric} on {claim.dataset}"
    actual = (
        "not captured" if verdict.actual_value is None else f"{verdict.actual_value:g}{claim.unit}"
    )
    attempts = (
        "\n".join(
            f"- Attempt {attempt.attempt}: `{attempt.outcome.phase}` / exit "
            f"`{attempt.outcome.exit_code}` — {attempt.proposal.diagnosis}"
            for attempt in verdict.attempts
        )
        or "- No debug retry was required."
    )
    # "Fixes applied: None" read as "nothing was ever tried" while the debug trail directly
    # above it described a runner script being written. The heading now states whether any
    # fix actually worked, and the list covers everything attempted.
    if verdict.fixes_applied:
        succeeded = verdict.status is VerdictStatus.VERIFIED
        fixes_heading = (
            "Fixes applied" if succeeded else "Fixes attempted (none produced a reproduction)"
        )
        fixes = "\n".join(f"- {fix}" for fix in verdict.fixes_applied)
    else:
        fixes_heading = "Fixes attempted"
        fixes = "- None. No patch was proposed or applied."

    # Multi-line output goes in a <details> block so the default view stays readable. Setup
    # chatter is already stripped upstream by failure_excerpt.
    rendered: list[str] = []
    for item in verdict.evidence:
        if "\n" in item or len(item) > 220:
            label, _, detail = item.partition(": ")
            rendered.append(
                f"<details><summary><code>{label or 'output'}</code></summary>\n\n"
                f"```\n{(detail or item).strip()}\n```\n\n</details>"
            )
        else:
            rendered.append(f"- {item}")
    evidence = "\n".join(rendered) or "- No metric evidence captured."
    body = f"""## Verity verdict

| Field | Result |
|---|---|
| Status | **{verdict.status.value}** |
| Confidence | {verdict.confidence.value} |
| Claimed | {claim.value:g}{claim.unit} |
| Reproduced | {actual} |
| Metric | {claim.metric} |
| Dataset | {claim.dataset} |

{verdict.summary}

### Source

- URL: {parsed_claim.source_url}
- Location: {claim.source_location}
- Evidence: {parsed_claim.evidence_excerpt}
- Conditions: {", ".join(claim.conditions) or "not stated"}

### Debug trail

{attempts}

### {fixes_heading}

{fixes}

### Execution evidence

{evidence}

---
Generated autonomously by Verity job `{job_id}`. A successful process alone is not treated
as proof; the verdict is based on the captured metric and the complete retry trail.
"""
    return title, body
