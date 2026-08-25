"""Google OIDC verification for authenticated Pub/Sub push delivery."""

from __future__ import annotations

import hmac
from typing import Any


class OidcVerificationUnavailable(RuntimeError):
    """Google's signing certificates could not be fetched for a transient reason."""


def verify_pubsub_oidc(
    authorization: str | None,
    *,
    audience: str,
    service_account_email: str,
) -> dict[str, Any]:
    """Verify signature, issuer, audience, and the exact Pub/Sub push identity."""

    if not authorization:
        raise ValueError("missing Pub/Sub OIDC bearer token")
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise ValueError("invalid Pub/Sub OIDC authorization header")

    from google.auth.exceptions import TransportError
    from google.auth.transport.requests import Request
    from google.oauth2 import id_token

    try:
        claims = dict(
            id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
                token.strip(), Request(), audience=audience
            )
        )
    except TransportError as exc:
        raise OidcVerificationUnavailable(
            "Pub/Sub OIDC verification is temporarily unavailable"
        ) from exc
    email = claims.get("email")
    email_verified = claims.get("email_verified")
    if (
        not isinstance(email, str)
        or not hmac.compare_digest(email, service_account_email)
        or email_verified is not True
    ):
        raise ValueError("Pub/Sub OIDC identity does not match the configured service account")
    return claims
