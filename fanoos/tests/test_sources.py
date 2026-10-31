"""Tests for fanoos.sources (network is mocked)."""

from __future__ import annotations

import httpx
import pytest

from fanoos import sources
from fanoos.errors import SourceError
from fanoos.sources import html_to_text, is_url, load_source

HTML = """<html><head><title>Negar · Portfolio</title><style>.x{}</style></head>
<body><h1>Case Studies</h1><script>alert(1)</script><p>Venture&nbsp;Compass</p>
<img src=a.png alt="Hero shot"></body></html>"""


def test_is_url() -> None:
    assert is_url("https://example.com") and is_url("HTTP://x.ir")
    assert not is_url("portfolio.pdf")


def test_html_to_text_strips_scripts_and_keeps_alt() -> None:
    text = html_to_text(HTML)
    assert text.startswith("Title: Negar · Portfolio")
    assert "Case Studies" in text and "Venture Compass" in text and "[image: Hero shot]" in text
    assert "alert" not in text and ".x{}" not in text


def test_url_is_fetched(monkeypatch) -> None:
    monkeypatch.setattr(
        sources.httpx, "get", lambda url, **kw: httpx.Response(200, text=HTML, request=httpx.Request("GET", url))
    )
    source = load_source("https://example.com")
    assert source.kind == "url" and "Case Studies" in source.text


def test_url_fetch_failure_falls_back_to_browsing(monkeypatch) -> None:
    def boom(url, **kw):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(sources.httpx, "get", boom)
    source = load_source("https://example.com")
    assert source.text == "" and "Could not fetch" in source.note


def test_no_fetch() -> None:
    assert load_source("https://example.com", fetch=False).text == ""


def test_missing_file(tmp_path) -> None:
    with pytest.raises(SourceError, match="No such file"):
        load_source(str(tmp_path / "nope.pdf"))


def test_non_pdf_file(tmp_path) -> None:
    path = tmp_path / "cv.docx"
    path.write_text("x")
    with pytest.raises(SourceError, match="not a PDF"):
        load_source(str(path))


def test_corrupt_pdf(tmp_path) -> None:
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"not a pdf")
    with pytest.raises(SourceError):
        load_source(str(path))


def test_pdf_text(tmp_path, monkeypatch) -> None:
    class Page:
        def extract_text(self) -> str:
            return "Product Designer — case study"

    class Reader:
        def __init__(self, path: str) -> None:
            self.pages = [Page(), Page()]

    import pypdf

    monkeypatch.setattr(pypdf, "PdfReader", Reader)
    path = tmp_path / "folio.pdf"
    path.write_bytes(b"%PDF-1.4")
    source = load_source(str(path))
    assert source.kind == "pdf" and "[Page 2]" in source.text
