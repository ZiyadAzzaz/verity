"""Input and filesystem boundaries for processing untrusted public repositories."""

from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from urllib.parse import SplitResult, urlsplit, urlunsplit


class UnsafeUrlError(ValueError):
    pass


def canonicalize_url(raw_url: str) -> str:
    parsed = urlsplit(raw_url.strip())
    if parsed.scheme.lower() != "https":
        raise UnsafeUrlError("only HTTPS source URLs are accepted")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("URLs containing credentials are not accepted")
    if not parsed.hostname:
        raise UnsafeUrlError("URL must include a hostname")
    host = parsed.hostname.encode("idna").decode("ascii").lower()
    port = parsed.port
    netloc = host if port in (None, 443) else f"{host}:{port}"
    path = parsed.path or "/"
    return urlunsplit(SplitResult("https", netloc, path, parsed.query, ""))


def validate_public_host(url: str) -> None:
    """Resolve every address and reject local, private, reserved, or metadata hosts."""

    parsed = urlsplit(url)
    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("URL must include a hostname")
    if host.lower() in {"localhost", "metadata.google.internal"}:
        raise UnsafeUrlError("local and metadata endpoints are blocked")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"could not resolve source host: {host}") from exc
    if not addresses:
        raise UnsafeUrlError(f"could not resolve source host: {host}")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise UnsafeUrlError(f"source host resolves to a non-public address: {address}")


def validate_repository_url(raw_url: str, allowed_hosts: tuple[str, ...]) -> str:
    url = canonicalize_url(raw_url)
    host = urlsplit(url).hostname or ""
    if host not in allowed_hosts:
        raise UnsafeUrlError(f"repository host {host!r} is not allowed")
    if host == "github.com":
        path_parts = [part for part in urlsplit(url).path.split("/") if part]
        if len(path_parts) < 2:
            raise UnsafeUrlError("GitHub repository URL must include owner and repository")
        return f"https://github.com/{path_parts[0]}/{path_parts[1].removesuffix('.git')}.git"
    return url


def safe_repo_path(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    candidate = (root / relative_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("path escapes the repository workspace")
    return candidate
