from __future__ import annotations

import io
import urllib.error

import pytest

from verity.identity_probe import (
    ApiProbe,
    IdentityProbeReport,
    _probe_api,
    decode_identity_report,
    encode_identity_report,
    run_identity_probe,
)


def test_identity_report_only_passes_explicit_api_denials() -> None:
    denied = IdentityProbeReport(
        service_account_email="sandbox@example.iam.gserviceaccount.com",
        metadata_token_obtained=True,
        probes=[ApiProbe(service="firestore", status_code=403, denied=True)],
    )
    inconclusive = denied.model_copy(
        update={"probes": [ApiProbe(service="firestore", denied=False, detail="timeout")]}
    )

    assert denied.passed is True
    assert inconclusive.passed is False
    assert decode_identity_report(encode_identity_report(denied)) == denied


def test_api_probe_accepts_403_but_not_404(monkeypatch) -> None:
    def forbidden(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            403,
            "forbidden",
            {},
            io.BytesIO(b"permission denied"),
        )

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    assert _probe_api("firestore", "https://firestore.googleapis.com/v1/x", "token").denied

    def missing(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            404,
            "missing",
            {},
            io.BytesIO(b"not found"),
        )

    monkeypatch.setattr("urllib.request.urlopen", missing)
    probe = _probe_api("firestore", "https://firestore.googleapis.com/v1/x", "token")
    assert probe.denied is False
    assert probe.status_code == 404


def test_api_probe_sends_mutating_probe_as_json(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def forbidden(request, timeout):
        captured.update(
            method=request.get_method(),
            data=request.data,
            content_type=request.get_header("Content-type"),
        )
        raise urllib.error.HTTPError(
            request.full_url,
            403,
            "forbidden",
            {},
            io.BytesIO(b"permission denied"),
        )

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    probe = _probe_api(
        "firestore_write",
        "https://firestore.googleapis.com/v1/projects/test/databases/(default)/documents:commit",
        "token",
        method="POST",
        body=b"{}",
    )

    assert probe.denied is True
    assert captured == {"method": "POST", "data": b"{}", "content_type": "application/json"}


@pytest.mark.parametrize(
    "project,region",
    [
        ("bad/project", "us-central1"),
        ("valid-project", "https://attacker.example"),
    ],
)
def test_identity_probe_rejects_untrusted_endpoint_components(project: str, region: str) -> None:
    with pytest.raises(ValueError, match="invalid"):
        run_identity_probe(project, region)
