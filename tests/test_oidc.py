from __future__ import annotations

import pytest
from google.oauth2 import id_token

from verity.oidc import verify_pubsub_oidc

AUDIENCE = "https://verity.internal/pubsub/project"
EMAIL = "verity-pubsub@project.iam.gserviceaccount.com"


def test_pubsub_oidc_verifies_audience_and_exact_email(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    def verify(token, request, *, audience):
        recorded.update(token=token, request=request, audience=audience)
        return {"email": EMAIL, "email_verified": True, "aud": audience}

    monkeypatch.setattr(id_token, "verify_oauth2_token", verify)

    claims = verify_pubsub_oidc(
        "Bearer signed-google-token",
        audience=AUDIENCE,
        service_account_email=EMAIL,
    )

    assert claims["email"] == EMAIL
    assert recorded["token"] == "signed-google-token"
    assert recorded["audience"] == AUDIENCE


@pytest.mark.parametrize(
    "authorization",
    [None, "", "Basic abc", "Bearer", "Bearer "],
)
def test_pubsub_oidc_rejects_missing_or_malformed_bearer_token(authorization) -> None:
    with pytest.raises(ValueError, match="OIDC"):
        verify_pubsub_oidc(
            authorization,
            audience=AUDIENCE,
            service_account_email=EMAIL,
        )


@pytest.mark.parametrize(
    "claims",
    [
        {"email": "attacker@example.com", "email_verified": True},
        {"email": EMAIL, "email_verified": False},
        {"email_verified": True},
    ],
)
def test_pubsub_oidc_rejects_the_wrong_or_unverified_identity(monkeypatch, claims) -> None:
    monkeypatch.setattr(id_token, "verify_oauth2_token", lambda *args, **kwargs: claims)

    with pytest.raises(ValueError, match="does not match"):
        verify_pubsub_oidc(
            "Bearer signed-google-token",
            audience=AUDIENCE,
            service_account_email=EMAIL,
        )
