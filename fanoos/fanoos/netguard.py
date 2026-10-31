"""Safe fetching of user-supplied URLs (SSRF protection).

The web server downloads portfolio pages on behalf of anonymous visitors, so a
URL must never be able to reach the server's own network: loopback, private
ranges, link-local (including cloud metadata at 169.254.169.254), carrier-grade
NAT, multicast or reserved addresses.

:func:`safe_fetch` enforces that on every hop:

* only ``http`` and ``https``, on any port;
* the host is resolved and **every** resolved address must be public;
* redirects are followed manually (at most :data:`MAX_REDIRECTS`), and each
  ``Location`` is validated the same way before it is requested;
* after connecting, the actual peer address is checked again, which defeats DNS
  rebinding (skipped only when an outbound HTTP proxy is configured, because
  the peer is then the proxy);
* only text/HTML responses are accepted and the body is capped at
  :data:`MAX_BYTES`, so a huge download cannot exhaust memory.
"""

from __future__ import annotations

import ipaddress
import os
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

from .errors import NetworkError, SourceError, bilingual

MAX_REDIRECTS: int = 5
MAX_BYTES: int = 3 * 1024 * 1024
ALLOWED_TYPES: tuple[str, ...] = ("text/html", "application/xhtml+xml", "text/plain")


class BlockedURLError(SourceError):
    """The URL (or a redirect target) points at a non-public address."""

    http_status = 400

    def __init__(self) -> None:
        super().__init__(
            bilingual(
                "Private, local or reserved addresses cannot be reviewed.",
                "آدرس‌های داخلی، محلی یا رزروشده قابل بررسی نیستند.",
            )
        )


@dataclass(frozen=True)
class FetchResult:
    """A fetched page: final URL after redirects, content type and decoded text."""

    url: str
    content_type: str
    text: str


def is_public_ip(value: str) -> bool:
    """Return ``True`` only for globally routable unicast addresses (IPv4-mapped IPv6 unwrapped)."""
    try:
        ip = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def check_url(url: str, *, allow_private: bool = False) -> None:
    """Validate scheme and host of ``url``; resolve the host and require public addresses.

    Raises:
        SourceError: The URL is not http(s) or has no host.
        BlockedURLError: A resolved address is not public.
        NetworkError: The host does not resolve.
    """
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        raise SourceError(bilingual("The URL must start with http:// or https://.", "لینک باید با https:// شروع شود."))
    if parts.username or parts.password:
        raise SourceError(
            bilingual("URLs with credentials are not accepted.", "لینک دارای نام کاربری/رمز پذیرفته نمی‌شود.")
        )
    if allow_private:
        return
    host = parts.hostname
    try:
        ipaddress.ip_address(host)
        literal = True
    except ValueError:
        literal = False
    if literal:
        if not is_public_ip(host):
            raise BlockedURLError()
        return
    try:
        infos = socket.getaddrinfo(
            host, parts.port or (443 if parts.scheme == "https" else 80), proto=socket.IPPROTO_TCP
        )
    except (socket.gaierror, UnicodeError) as exc:
        if _proxy_configured():
            # Proxy-only networks resolve names at the proxy; the proxy's egress policy applies.
            return
        raise NetworkError(bilingual(f"Could not resolve {host}.", f"دامنه‌ی {host} پیدا نشد.")) from exc
    if not infos or not all(is_public_ip(info[4][0]) for info in infos):
        raise BlockedURLError()


def _proxy_configured() -> bool:
    return any(os.environ.get(k) for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY"))


def _peer_ip(response: httpx.Response) -> str | None:
    stream = response.extensions.get("network_stream")
    if stream is None:
        return None
    try:
        addr = stream.get_extra_info("server_addr")
    except Exception:  # pragma: no cover - transport specific
        return None
    return addr[0] if addr else None


def safe_fetch(
    url: str,
    *,
    timeout: float = 20.0,
    allow_private: bool = False,
    max_bytes: int = MAX_BYTES,
    client: httpx.Client | None = None,
    user_agent: str = "Fanoos",
) -> FetchResult:
    """Fetch ``url`` with SSRF protection on every redirect hop.

    Args:
        url: The page to fetch.
        timeout: Seconds per request.
        allow_private: Skip the address checks (local development and the CLI only).
        max_bytes: Maximum body size to read.
        client: Optional preconfigured client (tests).
        user_agent: ``User-Agent`` header.

    Raises:
        BlockedURLError, SourceError, NetworkError: See :func:`check_url`; also for bad
            status codes, unsupported content types, oversized bodies and network failures.
    """
    own = client is None
    client = client or httpx.Client(timeout=timeout, follow_redirects=False, headers={"User-Agent": user_agent})
    check_peer = not allow_private and not _proxy_configured()
    try:
        current = url
        for _hop in range(MAX_REDIRECTS + 1):
            check_url(current, allow_private=allow_private)
            try:
                with client.stream("GET", current, follow_redirects=False) as response:
                    if check_peer:
                        peer = _peer_ip(response)
                        if peer is not None and not is_public_ip(peer):
                            raise BlockedURLError()
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise NetworkError(bilingual("Redirect without a target.", "تغییر مسیر بدون مقصد."))
                        current = urljoin(current, location)
                        continue
                    if response.status_code >= 400:
                        raise NetworkError(
                            bilingual(
                                f"The page answered HTTP {response.status_code}.",
                                f"صفحه با خطای HTTP {response.status_code} پاسخ داد.",
                            )
                        )
                    ctype = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    if ctype and ctype not in ALLOWED_TYPES:
                        raise SourceError(
                            bilingual(
                                f"The URL is not a web page ({ctype}). Upload PDFs with the PDF option.",
                                "این لینک صفحه‌ی وب نیست. فایل PDF را از گزینه‌ی PDF بارگذاری کنید.",
                            )
                        )
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > max_bytes:
                            raise SourceError(
                                bilingual("The page is too large to review.", "صفحه برای بررسی بیش از حد بزرگ است.")
                            )
                    encoding = response.encoding or "utf-8"
                    return FetchResult(str(response.url), ctype, bytes(body).decode(encoding, errors="replace"))
            except httpx.TimeoutException as exc:
                raise NetworkError(bilingual("The page took too long to respond.", "صفحه دیر پاسخ داد.")) from exc
            except httpx.HTTPError as exc:
                raise NetworkError(
                    bilingual(f"Could not reach the page ({exc.__class__.__name__}).", "اتصال به صفحه برقرار نشد.")
                ) from exc
        raise NetworkError(bilingual("Too many redirects.", "تعداد تغییر مسیرها بیش از حد است."))
    finally:
        if own:
            client.close()


__all__ = ["BlockedURLError", "FetchResult", "MAX_BYTES", "MAX_REDIRECTS", "check_url", "is_public_ip", "safe_fetch"]
