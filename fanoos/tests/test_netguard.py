"""SSRF protection tests for fanoos.netguard (DNS and HTTP are stubbed; no network)."""

from __future__ import annotations

import socket

import httpx
import pytest

from fanoos import netguard
from fanoos.errors import NetworkError, SourceError
from fanoos.netguard import BlockedURLError, check_url, is_public_ip, safe_fetch

PUBLIC = {"portfolio.example": "93.184.216.34", "cdn.example": "151.101.1.1"}
PRIVATE = {"intranet.example": "10.0.0.7", "rebind.example": "127.0.0.1"}


@pytest.fixture(autouse=True)
def fake_dns(monkeypatch):
    """Resolve the test hostnames without network, and run as if no outbound proxy exists."""
    for var in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY"):
        monkeypatch.delenv(var, raising=False)
    table = {**PUBLIC, **PRIVATE}

    def getaddrinfo(host, port, *args, **kwargs):
        if host not in table:
            raise socket.gaierror("not found")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (table[host], port))]

    monkeypatch.setattr(netguard.socket, "getaddrinfo", getaddrinfo)


def client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.1.2.3",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "100.64.0.1",
        "0.0.0.0",
        "::1",
        "fe80::1",
        "fc00::1",
        "::ffff:127.0.0.1",
        "224.0.0.1",
        "not-an-ip",
    ],
)
def test_non_public_addresses(ip: str) -> None:
    assert not is_public_ip(ip)


@pytest.mark.parametrize("ip", ["93.184.216.34", "1.1.1.1", "2606:4700:4700::1111"])
def test_public_addresses(ip: str) -> None:
    assert is_public_ip(ip)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]:8000/",
        "http://intranet.example/",
        "http://rebind.example/admin",
        "http://[::ffff:10.0.0.1]/",
    ],
)
def test_private_targets_are_blocked(url: str) -> None:
    with pytest.raises(BlockedURLError):
        check_url(url)


@pytest.mark.parametrize("url", ["ftp://portfolio.example/", "file:///etc/passwd", "javascript:alert(1)", "http://"])
def test_unsupported_urls(url: str) -> None:
    with pytest.raises(SourceError):
        check_url(url)


def test_credentials_in_url_are_rejected() -> None:
    with pytest.raises(SourceError, match="credentials"):
        check_url("https://user:pass@portfolio.example/")


def test_unresolvable_host_is_a_network_error() -> None:
    with pytest.raises(NetworkError):
        check_url("https://no-such-host.example/")


def test_allow_private_skips_address_checks() -> None:
    check_url("http://127.0.0.1:8000/", allow_private=True)


def test_fetches_public_page() -> None:
    result = safe_fetch(
        "https://portfolio.example/",
        client=client(lambda r: httpx.Response(200, html="<h1>Hi</h1>", headers={"content-type": "text/html"})),
    )
    assert result.text == "<h1>Hi</h1>" and result.content_type == "text/html"


def test_follows_public_redirects() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "portfolio.example":
            return httpx.Response(301, headers={"location": "https://cdn.example/folio"})
        return httpx.Response(200, text="ok", headers={"content-type": "text/plain"})

    assert safe_fetch("https://portfolio.example/", client=client(handler)).url == "https://cdn.example/folio"


@pytest.mark.parametrize(
    "location", ["http://127.0.0.1:8000/admin", "http://169.254.169.254/latest/", "http://intranet.example/"]
)
def test_redirect_to_private_address_is_blocked(location: str) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(302, headers={"location": location})

    with pytest.raises(BlockedURLError):
        safe_fetch("https://portfolio.example/", client=client(handler))
    assert calls == ["https://portfolio.example/"]  # the private target was never requested


def test_too_many_redirects() -> None:
    loop = client(lambda r: httpx.Response(302, headers={"location": "https://portfolio.example/again"}))
    with pytest.raises(NetworkError, match="redirects"):
        safe_fetch("https://portfolio.example/", client=loop)


def test_non_html_content_is_rejected() -> None:
    pdf = client(lambda r: httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"}))
    with pytest.raises(SourceError, match="not a web page"):
        safe_fetch("https://portfolio.example/cv.pdf", client=pdf)


def test_oversized_body_is_rejected() -> None:
    big = client(lambda r: httpx.Response(200, content=b"x" * 5000, headers={"content-type": "text/html"}))
    with pytest.raises(SourceError, match="too large"):
        safe_fetch("https://portfolio.example/", client=big, max_bytes=1000)


def test_http_error_status() -> None:
    with pytest.raises(NetworkError, match="404"):
        safe_fetch("https://portfolio.example/", client=client(lambda r: httpx.Response(404)))


def test_timeout_and_connection_errors() -> None:
    def slow(request):
        raise httpx.ReadTimeout("slow", request=request)

    def down(request):
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(NetworkError, match="too long"):
        safe_fetch("https://portfolio.example/", client=client(slow))
    with pytest.raises(NetworkError, match="reach"):
        safe_fetch("https://portfolio.example/", client=client(down))


def test_rebinding_peer_check(monkeypatch) -> None:
    """Even if DNS said 'public', a connection that lands on a private peer is refused."""
    monkeypatch.setattr(netguard, "_peer_ip", lambda response: "127.0.0.1")
    ok = client(lambda r: httpx.Response(200, text="secret", headers={"content-type": "text/html"}))
    with pytest.raises(BlockedURLError):
        safe_fetch("https://portfolio.example/", client=ok)
