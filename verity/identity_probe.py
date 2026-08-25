"""Adversarial Cloud Run sandbox identity probe.

This module intentionally obtains the task's metadata-server access token and tries the Google
Cloud APIs that would matter to Verity.  It never prints or persists the token.  A passing report
requires metadata identity to work while every project API rejects that identity.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

IDENTITY_LOG_PREFIX = "VERITY_SANDBOX_IDENTITY_V1="
METADATA_ROOT = "http://metadata.google.internal/computeMetadata/v1"


class ApiProbe(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    service: str
    status_code: int | None = None
    denied: bool
    detail: str = Field(default="", max_length=500)


class IdentityProbeReport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    version: Literal[1] = 1
    service_account_email: str
    metadata_token_obtained: bool
    probes: list[ApiProbe]

    @property
    def passed(self) -> bool:
        return (
            self.metadata_token_obtained
            and bool(self.probes)
            and all(probe.denied for probe in self.probes)
        )


def _metadata_text(path: str) -> str:
    request = urllib.request.Request(
        f"{METADATA_ROOT}/{path}",
        headers={"Metadata-Flavor": "Google"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return bytes(response.read(100_000)).decode("utf-8")


def _probe_api(
    service: str,
    url: str,
    token: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
) -> ApiProbe:
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        url,
        headers=headers,
        data=body,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            detail = response.read(500).decode("utf-8", errors="replace")
            return ApiProbe(
                service=service,
                status_code=response.status,
                denied=False,
                detail=f"unexpectedly allowed: {detail}"[:500],
            )
    except urllib.error.HTTPError as exc:
        detail = exc.read(500).decode("utf-8", errors="replace")
        return ApiProbe(
            service=service,
            status_code=exc.code,
            denied=exc.code in {401, 403},
            detail=detail[:500],
        )
    except (OSError, urllib.error.URLError) as exc:
        # A network failure is not proof of least privilege. The acceptance test requires an
        # explicit authentication/authorization denial from every reachable Google API.
        return ApiProbe(service=service, denied=False, detail=f"request failed: {exc}"[:500])


def run_identity_probe(project: str, region: str) -> IdentityProbeReport:
    """Use a stolen metadata token and require explicit denial from sensitive APIs."""

    if not re.fullmatch(r"(?:[a-z][a-z0-9-]{4,28}[a-z0-9]|[0-9]{6,20})", project):
        raise ValueError("identity probe project is invalid")
    if not re.fullmatch(r"[a-z]+-[a-z0-9]+[0-9]", region):
        raise ValueError("identity probe region is invalid")
    encoded_project = urllib.parse.quote(project, safe="")
    encoded_region = urllib.parse.quote(region, safe="")
    email = _metadata_text("instance/service-accounts/default/email").strip()
    token_document = json.loads(_metadata_text("instance/service-accounts/default/token"))
    token = token_document.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("metadata server returned no access token")

    firestore_document = (
        f"projects/{encoded_project}/databases/(default)/documents/"
        "verity_sandbox_security_probe/forbidden"
    )
    targets = [
        (
            "firestore_write",
            f"https://firestore.googleapis.com/v1/projects/{encoded_project}/"
            "databases/(default)/documents:commit",
            "POST",
            json.dumps(
                {
                    "writes": [
                        {
                            "update": {
                                "name": firestore_document,
                                "fields": {"probe": {"booleanValue": True}},
                            }
                        }
                    ]
                },
                separators=(",", ":"),
            ).encode("utf-8"),
        ),
        (
            "secret_manager_read",
            f"https://secretmanager.googleapis.com/v1/projects/{encoded_project}/"
            "secrets/verity-sandbox-deny-probe/versions/latest:access",
            "GET",
            None,
        ),
        (
            "pubsub_publish",
            f"https://pubsub.googleapis.com/v1/projects/{encoded_project}/topics/"
            "verification-jobs:publish",
            "POST",
            b'{"messages":[{"data":"c2FuZGJveC1pZGVudGl0eS1wcm9iZQ=="}]}',
        ),
        (
            "cloud_run_execute",
            f"https://run.googleapis.com/v2/projects/{encoded_project}/locations/"
            f"{encoded_region}/jobs/verity-sandbox:run",
            "POST",
            b"{}",
        ),
        (
            "vertex_ai_list",
            f"https://{encoded_region}-aiplatform.googleapis.com/v1/projects/"
            f"{encoded_project}/locations/{encoded_region}/models",
            "GET",
            None,
        ),
        (
            "cloud_storage_list",
            f"https://storage.googleapis.com/storage/v1/b?project={encoded_project}",
            "GET",
            None,
        ),
    ]
    return IdentityProbeReport(
        service_account_email=email,
        metadata_token_obtained=True,
        probes=[
            _probe_api(service, url, token, method=method, body=body)
            for service, url, method, body in targets
        ],
    )


def encode_identity_report(report: IdentityProbeReport) -> str:
    return IDENTITY_LOG_PREFIX + report.model_dump_json()


def decode_identity_report(line: str) -> IdentityProbeReport:
    if not line.startswith(IDENTITY_LOG_PREFIX):
        raise ValueError("log entry is not a Verity sandbox identity report")
    return IdentityProbeReport.model_validate_json(line[len(IDENTITY_LOG_PREFIX) :].strip())
