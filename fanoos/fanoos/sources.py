"""Loading portfolio input: a URL or a local PDF.

For a URL, Fanoos fetches the page and extracts its visible text so the model
sees the actual copy. The URL is always passed along too, so the model can open
it with ``web_search`` if the fetch fails or the page is rendered by JavaScript.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Literal

from .errors import NetworkError, SourceError

MAX_CHARS: int = 60_000
"""Upper bound on extracted text sent to the model, to keep requests affordable."""

USER_AGENT: str = "Fanoos/0.3 (+https://github.com/zahednegar-hub/fanoos)"


@dataclass(frozen=True)
class PortfolioSource:
    """A portfolio ready to be reviewed.

    Attributes:
        kind: ``"url"`` or ``"pdf"``.
        location: The URL, or the PDF's absolute path.
        text: Extracted text, possibly empty (for example a JavaScript-only page).
        note: Optional explanation shown to the model, such as why text is missing.
    """

    kind: Literal["url", "pdf"]
    location: str
    text: str
    note: str = ""


def is_url(target: str) -> bool:
    """Return ``True`` if ``target`` looks like an http(s) URL."""
    return bool(re.match(r"^https?://", target.strip(), re.I))


def load_source(
    target: str, *, timeout: float = 20.0, fetch: bool = True, allow_private: bool = True
) -> PortfolioSource:
    """Turn a CLI target (URL or PDF path) into a :class:`PortfolioSource`.

    Args:
        target: An ``http(s)://`` URL or a path to a ``.pdf`` file.
        timeout: Seconds to wait when fetching a URL.
        fetch: If ``False``, do not download URLs (the model browses them itself).
        allow_private: Allow loopback/private URLs (CLI default); the web server passes ``False``.

    Returns:
        The loaded source.

    Raises:
        SourceError: If the path is missing, is not a PDF, or cannot be read.
    """
    target = target.strip()
    if is_url(target):
        if not fetch:
            return PortfolioSource("url", target, "", "Page was not pre-fetched; open it with web_search.")
        try:
            return PortfolioSource("url", target, fetch_page_text(target, timeout=timeout, allow_private=allow_private))
        except NetworkError as exc:
            return PortfolioSource("url", target, "", f"Could not fetch the page directly ({exc}).")

    path = Path(target).expanduser()
    if not path.exists():
        raise SourceError(f"No such file: {path}. Pass a portfolio URL (https://...) or a PDF path.")
    if path.suffix.lower() != ".pdf":
        raise SourceError(f"{path.name} is not a PDF. Fanoos reviews portfolio URLs and PDF files.")
    return PortfolioSource("pdf", str(path.resolve()), read_pdf_text(path))


def read_pdf_text(path: Path) -> str:
    """Extract the text of every page of a PDF.

    Args:
        path: Path to the PDF.

    Returns:
        The text, pages separated by blank lines, truncated to :data:`MAX_CHARS`.

    Raises:
        SourceError: If the file is not a readable PDF or has no extractable text.
    """
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(str(path))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
    except (PdfReadError, OSError, ValueError) as exc:
        raise SourceError(f"Could not read {path.name} as a PDF: {exc}") from exc

    text = "\n\n".join(f"[Page {i}]\n{p}" for i, p in enumerate(pages, 1) if p)
    if not text:
        raise SourceError(
            f"{path.name} has no extractable text (it may be image-only). "
            "Export the portfolio with live text, or review its URL instead."
        )
    return text[:MAX_CHARS]


class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript", "svg", "template", "head"}
    _BLOCK = {
        "p",
        "div",
        "section",
        "article",
        "li",
        "br",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "tr",
        "header",
        "footer",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title = ""
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._in_title = True
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag in self._BLOCK:
            self.parts.append("\n")
        elif tag == "img":
            alt = dict(attrs).get("alt")
            if alt:
                self.parts.append(f" [image: {alt}] ")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag in self._BLOCK:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        elif not self._skip_depth:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    """Extract readable text (including image alt text) from an HTML document."""
    parser = _TextExtractor()
    parser.feed(html)
    body = "".join(parser.parts)
    lines = [re.sub(r"[ \t ]+", " ", line).strip() for line in body.splitlines()]
    text = "\n".join(line for line in lines if line)
    title = parser.title.strip()
    return f"Title: {title}\n\n{text}" if title else text


def fetch_page_text(url: str, *, timeout: float = 20.0, allow_private: bool = True) -> str:
    """Download ``url`` (with SSRF protection unless ``allow_private``) and return its visible text.

    Args:
        url: The page to fetch.
        timeout: Seconds to wait per request.
        allow_private: Allow loopback/private targets. The CLI allows them (it runs on your own
            machine); the web server never does.

    Returns:
        Extracted text truncated to :data:`MAX_CHARS`.

    Raises:
        BlockedURLError: The URL or a redirect points at a non-public address.
        NetworkError: On connection failures, timeouts, or HTTP error statuses.
        SourceError: The response is not a web page or is too large.
    """
    from .netguard import safe_fetch

    result = safe_fetch(url, timeout=timeout, allow_private=allow_private, user_agent=USER_AGENT)
    if result.content_type == "text/plain":
        return result.text[:MAX_CHARS]
    return html_to_text(result.text)[:MAX_CHARS]


__all__ = ["PortfolioSource", "MAX_CHARS", "is_url", "load_source", "read_pdf_text", "html_to_text", "fetch_page_text"]
