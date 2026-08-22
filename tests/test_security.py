from __future__ import annotations

import socket

import pytest

from verity.security import (
    UnsafeUrlError,
    canonicalize_url,
    safe_repo_path,
    validate_public_host,
    validate_repository_url,
)


def test_canonicalize_removes_fragment_and_default_port() -> None:
    assert (
        canonicalize_url(" HTTPS://Example.COM:443/a?q=1#fragment ") == "https://example.com/a?q=1"
    )


@pytest.mark.parametrize(
    "url",
    ["http://example.com", "https://user:pass@example.com", "file:///etc/passwd"],
)
def test_canonicalize_rejects_unsafe_schemes_and_credentials(url: str) -> None:
    with pytest.raises(UnsafeUrlError):
        canonicalize_url(url)


def test_public_host_rejects_private_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )
    with pytest.raises(UnsafeUrlError, match="non-public"):
        validate_public_host("https://example.com/")


def test_repository_allowlist_and_normalization() -> None:
    assert (
        validate_repository_url("https://github.com/owner/repo/tree/main", ("github.com",))
        == "https://github.com/owner/repo.git"
    )
    with pytest.raises(UnsafeUrlError, match="not allowed"):
        validate_repository_url("https://gitlab.com/owner/repo", ("github.com",))


def test_safe_repo_path_rejects_escape(tmp_path) -> None:
    with pytest.raises(ValueError, match="escapes"):
        safe_repo_path(tmp_path, "../outside")
