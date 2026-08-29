"""A revocable second API key, so a judge's credential is not the owner's credential.

Verity previously accepted exactly one key. Handing that key to judges would mean the only
way to revoke their access is rotating the owner's own credential and redeploying. A separate
`VERITY_JUDGE_TEST_KEY` can be revoked on its own.

Two properties matter more than the feature itself:

* both keys must be compared in constant time, exactly as the single key was; and
* an empty or unset judge key must never become a valid credential, which is the obvious way
  a "second key" feature turns into an authentication bypass.
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from verity.config import Settings


def settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "_env_file": None,
        "environment": "development",
        "env": "local",
        "api_key": SecretStr("owner-key-that-is-long-enough-01"),
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


class TestAcceptedKeys:
    def test_the_owner_key_is_accepted(self) -> None:
        assert settings().accepts_api_key("owner-key-that-is-long-enough-01")

    def test_the_judge_key_is_accepted_when_configured(self) -> None:
        s = settings(judge_test_key=SecretStr("judge-key-that-is-long-enough-02"))
        assert s.accepts_api_key("judge-key-that-is-long-enough-02")
        assert s.accepts_api_key("owner-key-that-is-long-enough-01"), "owner key still works"

    def test_an_unrelated_key_is_rejected(self) -> None:
        s = settings(judge_test_key=SecretStr("judge-key-that-is-long-enough-02"))
        assert not s.accepts_api_key("some-other-value")

    @pytest.mark.parametrize("supplied", ["", None])
    def test_empty_or_missing_input_is_always_rejected(self, supplied: str | None) -> None:
        s = settings(judge_test_key=SecretStr("judge-key-that-is-long-enough-02"))
        assert not s.accepts_api_key(supplied)

    def test_an_empty_judge_key_never_becomes_a_credential(self) -> None:
        """The bypass this feature could otherwise introduce."""
        s = settings(judge_test_key=SecretStr(""))
        assert not s.accepts_api_key("")
        assert s.accepts_api_key("owner-key-that-is-long-enough-01")

    def test_an_absent_judge_key_changes_nothing(self) -> None:
        s = settings(judge_test_key=None)
        assert s.accepts_api_key("owner-key-that-is-long-enough-01")
        assert not s.accepts_api_key("anything-else")

    def test_revoking_the_judge_key_leaves_the_owner_key_working(self) -> None:
        """The whole point: independent revocation."""
        live = settings(judge_test_key=SecretStr("judge-key-that-is-long-enough-02"))
        revoked = settings(judge_test_key=None)
        assert live.accepts_api_key("judge-key-that-is-long-enough-02")
        assert not revoked.accepts_api_key("judge-key-that-is-long-enough-02")
        assert revoked.accepts_api_key("owner-key-that-is-long-enough-01")


class TestProductionRules:
    def test_production_still_requires_the_owner_key(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="VERITY_API_KEY"):
            Settings(
                _env_file=None,  # type: ignore[call-arg]
                environment="production",
                env="cloud",
                google_cloud_project="verity-506800",
                api_key=None,
                pubsub_oidc_audience="https://verity.internal/pubsub/verity-506800",
                pubsub_service_account="verity-pubsub@verity-506800.iam.gserviceaccount.com",
                github_token=SecretStr("t"),
                report_repo="owner/repo",
            )

    def test_a_short_judge_key_is_refused_in_production(self) -> None:
        """A weak shared credential on a public endpoint is worse than none."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="VERITY_JUDGE_TEST_KEY"):
            Settings(
                _env_file=None,  # type: ignore[call-arg]
                environment="production",
                env="cloud",
                google_cloud_project="verity-506800",
                api_key=SecretStr("x" * 24),
                judge_test_key=SecretStr("short"),
                pubsub_oidc_audience="https://verity.internal/pubsub/verity-506800",
                pubsub_service_account="verity-pubsub@verity-506800.iam.gserviceaccount.com",
                github_token=SecretStr("t"),
                report_repo="owner/repo",
            )


class TestHttpSurface:
    """The dependency actually wired into the routes, not just the helper."""

    def _client(self, **overrides: object):
        import warnings

        from fastapi.testclient import TestClient

        from verity.api import create_app
        from verity.container import build_container

        warnings.filterwarnings("ignore")
        s = settings(**overrides)
        return TestClient(create_app(settings=s, container=build_container(s)))

    def test_either_key_reaches_the_route_and_a_wrong_one_does_not(self, tmp_path) -> None:
        client = self._client(
            judge_test_key=SecretStr("judge-key-that-is-long-enough-02"),
            sqlite_path=str(tmp_path / "v.db"),
        )
        with client:
            for key in ("owner-key-that-is-long-enough-01", "judge-key-that-is-long-enough-02"):
                r = client.get("/api/jobs/missing", headers={"X-Verity-Key": key})
                assert r.status_code == 404, "authenticated, so it reaches the handler"
            assert (
                client.get("/api/jobs/missing", headers={"X-Verity-Key": "nope"}).status_code == 401
            )
            assert client.get("/api/jobs/missing").status_code == 401
