"""Tests for the FastAPI server (no network: the agent uses a fake client)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from fanoos import server
from fanoos.agent import Fanoos
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


@pytest.fixture
def fake(sample_reply: str):
    client = FakeClient(chat_chunks(sample_reply))
    server.app.dependency_overrides[server.default_agent_factory] = lambda: (
        lambda provider, model: Fanoos(provider=provider or "gemini", model=model, client=client)
    )
    yield client
    server.app.dependency_overrides.clear()


@pytest.fixture
def api() -> TestClient:
    return TestClient(server.app)


def test_index_and_assets(api: TestClient) -> None:
    page = api.get("/")
    assert page.status_code == 200 and 'lang="fa" dir="rtl"' in page.text
    assert "/assets/logo-full.svg" in page.text and "/assets/favicon.svg" in page.text
    for path in ("/static/styles.css", "/static/app.js", "/assets/logo-full.svg", "/favicon.ico"):
        assert api.get(path).status_code == 200, path


def test_health_without_keys(api: TestClient) -> None:
    assert api.get("/health").json() == {"status": "ok", "version": "0.2.0", "provider": None, "live_search": None}


def test_health_and_providers_with_key(api: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert api.get("/health").json()["provider"] == "gemini"
    data = api.get("/api/providers").json()
    assert data["selected"] == "gemini"
    assert {p["name"]: p["configured"] for p in data["providers"]} == {"xai": False, "gemini": True, "groq": False}
    assert "test-key" not in str(data)


def test_review_json_url(api: TestClient, fake: FakeClient, monkeypatch) -> None:
    monkeypatch.setattr(server, "_private_host", lambda url: False)
    monkeypatch.setattr(server, "load_source", lambda target: PortfolioSource("url", target, "Case studies"))
    res = api.post("/api/review", json={"url": "https://example.com", "lang": "en"})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["scores"]["visual_craft"] == 84 and data["overall_score"] == 67
    assert data["provider"] == "gemini" and data["live_search"] is False
    assert data["report"].endswith(NO_LIVE_SEARCH_FOOTER)
    assert "English" in fake.responses.calls[0]["messages"][1]["content"]


def test_review_form_pdf_upload(api: TestClient, fake: FakeClient) -> None:
    pdf = make_pdf("Senior Product Designer case study")
    res = api.post("/api/review", data={"lang": "fa"}, files={"file": ("folio.pdf", pdf, "application/pdf")})
    assert res.status_code == 200, res.text
    user = fake.responses.calls[0]["messages"][1]["content"]
    assert "Senior Product Designer case study" in user and "Portfolio PDF" in user


def test_missing_input(api: TestClient, fake: FakeClient) -> None:
    res = api.post("/api/review", data={"lang": "fa"})
    assert res.status_code == 400 and res.json()["type"] == "SourceError"


def test_bad_url_and_lang(api: TestClient, fake: FakeClient) -> None:
    assert api.post("/api/review", json={"url": "ftp://x"}).status_code == 400
    assert api.post("/api/review", json={"url": "https://example.com", "lang": "de"}).status_code == 400


def test_private_url_refused(api: TestClient, fake: FakeClient) -> None:
    res = api.post("/api/review", json={"url": "http://127.0.0.1:8000/admin"})
    assert res.status_code == 400 and "local" in res.json()["error"]


def test_non_pdf_upload(api: TestClient, fake: FakeClient) -> None:
    res = api.post("/api/review", files={"file": ("cv.docx", b"PK\x03\x04", "application/octet-stream")})
    assert res.status_code == 400 and "PDF" in res.json()["error"]


def test_too_large_upload(api: TestClient, fake: FakeClient, monkeypatch) -> None:
    monkeypatch.setattr(server, "MAX_UPLOAD_BYTES", 10)
    res = api.post("/api/review", files={"file": ("big.pdf", b"%PDF-" + b"x" * 50, "application/pdf")})
    assert res.status_code == 413


def test_invalid_json(api: TestClient, fake: FakeClient) -> None:
    res = api.post("/api/review", content=b"{nope", headers={"content-type": "application/json"})
    assert res.status_code == 400


def test_missing_key_is_bilingual_503(api: TestClient) -> None:
    res = api.post("/api/review", json={"url": "https://example.com"})
    assert res.status_code == 503
    body = res.json()
    assert body["type"] == "MissingAPIKeyError" and "GEMINI_API_KEY" in body["error"] and "کلید" in body["error"]


def test_malformed_output_502(api: TestClient, monkeypatch) -> None:
    client = FakeClient(chat_chunks("nothing structured here"))
    server.app.dependency_overrides[server.default_agent_factory] = lambda: (
        lambda provider, model: Fanoos(provider="groq", client=client)
    )
    monkeypatch.setattr(server, "_private_host", lambda url: False)
    monkeypatch.setattr(server, "load_source", lambda target: PortfolioSource("url", target, ""))
    try:
        res = api.post("/api/review", json={"url": "https://example.com"})
    finally:
        server.app.dependency_overrides.clear()
    assert res.status_code == 502 and res.json()["type"] == "MalformedOutputError"


def test_private_host_detection() -> None:
    assert server._private_host("http://127.0.0.1/")
    assert server._private_host("http://localhost:8000/")
    assert server._private_host("http://10.0.0.5/")
    assert not server._private_host("http://no-such-host.invalid/")
