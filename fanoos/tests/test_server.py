"""Tests for the FastAPI server (no network: the agent uses a fake client)."""

from __future__ import annotations

import dataclasses

import pytest
from fastapi.testclient import TestClient

from fanoos import __version__, server
from fanoos.agent import Fanoos
from fanoos.settings import Settings, load_settings
from fanoos.sources import PortfolioSource
from fanoos.system_prompt import NO_LIVE_SEARCH_FOOTER

from .conftest import FakeClient, chat_chunks


def make_pdf(text: str) -> bytes:
    """Build a minimal one-page PDF containing ``text`` (ASCII)."""
    stream = f"BT /F1 18 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


def settings(**overrides) -> Settings:
    base = dataclasses.replace(load_settings(), rate_limit=(0, 0), env="production")
    return dataclasses.replace(base, **overrides)


@pytest.fixture
def app_factory(sample_reply: str):
    """Build a fresh app (own settings, own limiter) whose agent uses a fake client."""
    made = []

    def make(reply: str = sample_reply, **overrides):
        app = server.create_app(settings(**overrides))
        client = FakeClient(chat_chunks(reply))
        app.dependency_overrides[server.default_agent_factory] = lambda: (
            lambda provider, model: Fanoos(provider=provider or "gemini", model=model, client=client)
        )
        app.state.fake = client
        made.append(app)
        return app

    return make


@pytest.fixture
def fake(app_factory, monkeypatch):
    app = app_factory()
    monkeypatch.setattr(server, "check_url", lambda url, allow_private=False: None)  # no DNS in tests
    return app


@pytest.fixture
def api(request) -> TestClient:
    app = request.getfixturevalue("fake") if "fake" in request.fixturenames else server.create_app(settings())
    return TestClient(app)


def test_index_and_assets(api: TestClient) -> None:
    page = api.get("/")
    assert page.status_code == 200 and 'lang="fa" dir="rtl"' in page.text
    assert "/assets/logo-full.svg" in page.text and "/assets/favicon.svg" in page.text
    for path in (
        "/static/styles.css",
        "/static/app.js",
        "/static/lantern3d.js",
        "/static/vendor/three/three.module.min.js",
        "/static/vendor/three/addons/postprocessing/EffectComposer.js",
        "/static/vendor/three/addons/postprocessing/UnrealBloomPass.js",
        "/static/vendor/three/addons/environments/RoomEnvironment.js",
        "/static/fonts/inter-latin-wght-normal.woff2",
        "/static/fonts/vazirmatn-arabic-400-normal.woff2",
        "/assets/logo-full.svg",
        "/favicon.ico",
    ):
        assert api.get(path).status_code == 200, path


def test_page_wires_the_lantern(api: TestClient) -> None:
    page = api.get("/").text
    assert '"three": "/static/vendor/three/three.module.min.js"' in page  # import map
    assert 'id="lantern-stage"' in page and "hero-fallback" in page  # 3D stage + no-WebGL fallback
    app = api.get("/static/app.js").text
    assert 'import("/static/lantern3d.js")' in app and "setMode(" in app and "setScroll(" in app
    assert ".innerHTML" not in app and "insertAdjacentHTML" not in app  # model output is inserted as text only


def test_health_without_keys(api: TestClient) -> None:
    assert api.get("/health").json() == {"status": "ok", "version": __version__, "provider": None, "live_search": None}


def test_health_and_providers_with_key(api: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert api.get("/health").json()["provider"] == "gemini"
    data = api.get("/api/providers").json()
    assert data["selected"] == "gemini"
    assert {p["name"]: p["configured"] for p in data["providers"]} == {"xai": False, "gemini": True, "groq": False}
    assert "test-key" not in str(data)


def test_review_json_url(api: TestClient, fake, monkeypatch) -> None:
    monkeypatch.setattr(server, "load_source", lambda target, allow_private=False: PortfolioSource("url", target, "x"))
    res = api.post("/api/review", json={"url": "https://example.com", "lang": "en"})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["scores"]["visual_craft"] == 84 and data["overall_score"] == 67
    assert data["provider"] == "gemini" and data["live_search"] is False
    assert data["report"].endswith(NO_LIVE_SEARCH_FOOTER)
    assert "English" in fake.state.fake.responses.calls[0]["messages"][1]["content"]


def test_review_form_pdf_upload(api: TestClient, fake) -> None:
    pdf = make_pdf("Senior Product Designer case study")
    res = api.post("/api/review", data={"lang": "fa"}, files={"file": ("my folio.pdf", pdf, "application/pdf")})
    assert res.status_code == 200, res.text
    user = fake.state.fake.responses.calls[0]["messages"][1]["content"]
    assert "Senior Product Designer case study" in user and "Portfolio PDF: my folio.pdf" in user
    assert "/tmp" not in user and "fanoos-" not in user  # no server paths reach the model


def test_missing_input(api: TestClient, fake) -> None:
    res = api.post("/api/review", data={"lang": "fa"})
    assert res.status_code == 400 and res.json()["type"] == "SourceError"


def test_bad_url_and_lang(api: TestClient, fake) -> None:
    assert api.post("/api/review", json={"url": "ftp://x"}).status_code == 400
    assert api.post("/api/review", json={"url": "https://example.com", "lang": "de"}).status_code == 400


def test_private_url_refused() -> None:
    api = TestClient(server.create_app(settings()))
    for url in ("http://127.0.0.1:8000/admin", "http://169.254.169.254/latest/meta-data/", "http://[::1]/"):
        res = api.post("/api/review", json={"url": url})
        assert res.status_code == 400 and res.json()["type"] == "BlockedURLError", url


def test_non_pdf_upload(api: TestClient, fake) -> None:
    res = api.post("/api/review", files={"file": ("cv.docx", b"PK\x03\x04", "application/octet-stream")})
    assert res.status_code == 400 and "PDF" in res.json()["error"]


def test_too_large_upload(app_factory) -> None:
    api = TestClient(app_factory(max_upload_bytes=1024))
    res = api.post("/api/review", files={"file": ("big.pdf", b"%PDF-" + b"x" * 5000, "application/pdf")})
    assert res.status_code == 413
    huge = api.post("/api/review", content=b"x" * 200_000, headers={"content-type": "application/json"})
    assert huge.status_code == 413  # rejected by the streaming body limit


def test_invalid_json(api: TestClient, fake) -> None:
    res = api.post("/api/review", content=b"{nope", headers={"content-type": "application/json"})
    assert res.status_code == 400


def test_missing_key_is_bilingual_503(api: TestClient) -> None:
    res = api.post("/api/review", json={"url": "https://example.com"})
    assert res.status_code == 503
    body = res.json()
    assert body["type"] == "MissingAPIKeyError" and "GEMINI_API_KEY" in body["error"] and "کلید" in body["error"]


def test_malformed_output_502(app_factory, monkeypatch) -> None:
    monkeypatch.setattr(server, "check_url", lambda url, allow_private=False: None)
    monkeypatch.setattr(server, "load_source", lambda target, allow_private=False: PortfolioSource("url", target, ""))
    api = TestClient(app_factory(reply="nothing structured here"))
    res = api.post("/api/review", json={"url": "https://example.com"})
    assert res.status_code == 502 and res.json()["type"] == "MalformedOutputError"


def test_security_headers_and_csp_hash(api: TestClient) -> None:
    import base64
    import hashlib
    import re

    res = api.get("/")
    csp = res.headers["content-security-policy"]
    importmap = re.search(r'<script type="importmap">(.*?)</script>', res.text, re.S).group(1)
    digest = base64.b64encode(hashlib.sha256(importmap.encode()).digest()).decode()
    assert f"'sha256-{digest}'" in csp and "'unsafe-inline'" not in csp.split("script-src", 1)[1].split(";")[0]
    assert "frame-ancestors 'none'" in csp and "object-src 'none'" in csp
    assert res.headers["x-content-type-options"] == "nosniff" and res.headers["x-frame-options"] == "DENY"
    assert "strict-transport-security" not in res.headers  # only over HTTPS
    assert "access-control-allow-origin" not in res.headers  # no CORS


def test_hsts_over_https() -> None:
    api = TestClient(server.create_app(settings()), base_url="https://fanoos.example")
    assert "max-age=" in api.get("/health").headers["strict-transport-security"]


def test_docs_only_in_development() -> None:
    assert TestClient(server.create_app(settings())).get("/docs").status_code == 404
    assert TestClient(server.create_app(settings(env="development"))).get("/docs").status_code == 200


def test_rate_limit(app_factory, monkeypatch) -> None:
    monkeypatch.setattr(server, "check_url", lambda url, allow_private=False: None)
    monkeypatch.setattr(server, "load_source", lambda target, allow_private=False: PortfolioSource("url", target, "x"))
    api = TestClient(app_factory(rate_limit=(2, 3600)))
    codes = [api.post("/api/review", json={"url": "https://example.com"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    last = api.post("/api/review", json={"url": "https://example.com"})
    assert last.json()["type"] == "RateLimitedError" and int(last.headers["retry-after"]) > 0


def test_rate_limiter_window() -> None:
    limiter = server.RateLimiter(1, 1)
    limiter.check("a")
    limiter.check("b")  # separate clients
    with pytest.raises(server.RateLimitedError):
        limiter.check("a")


def test_production_ignores_client_model_choice(api: TestClient, fake, monkeypatch) -> None:
    monkeypatch.setattr(server, "load_source", lambda target, allow_private=False: PortfolioSource("url", target, "x"))
    res = api.post("/api/review", json={"url": "https://example.com", "model": "very-expensive-model"})
    assert res.status_code == 200 and fake.state.fake.responses.calls[0]["model"] != "very-expensive-model"


def test_unexpected_errors_are_generic(app_factory, monkeypatch) -> None:
    monkeypatch.setattr(server, "check_url", lambda url, allow_private=False: None)

    def explode(target, allow_private=False):
        raise RuntimeError("/srv/secret/path failed")

    monkeypatch.setattr(server, "load_source", explode)
    api = TestClient(app_factory(), raise_server_exceptions=False)
    res = api.post("/api/review", json={"url": "https://example.com"})
    assert res.status_code == 500 and res.json()["type"] == "InternalError"
    assert "/srv/secret" not in res.text


def test_errors_never_contain_keys(monkeypatch) -> None:
    from fanoos.errors import APIError, redact

    monkeypatch.setenv("GEMINI_API_KEY", "test-value-0123456789")
    assert "test-value-0123456789" not in redact("provider said: key test-value-0123456789 invalid")
    assert "[redacted]" in redact("token gsk_" + "a" * 20)
    app = server.create_app(settings())

    @app.get("/boom")
    def boom():
        raise APIError("upstream echoed test-value-0123456789")

    res = TestClient(app).get("/boom")
    assert "test-value-0123456789" not in res.text


def test_health_does_not_leak_settings(api: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-value-0123456789")
    body = api.get("/health").text
    assert "test-value" not in body and "rate" not in body and "/home" not in body


def test_rejects_other_content_types(api: TestClient, fake) -> None:
    res = api.post("/api/review", content=b"url=x", headers={"content-type": "text/plain"})
    assert res.status_code == 400
