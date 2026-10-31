"""FastAPI server: the web UI plus a JSON API for reviews.

Run it from the repository root::

    uvicorn server:app --reload

Endpoints:

* ``GET /`` serves ``web/index.html``; ``/static`` and ``/assets`` serve the UI files and logos.
* ``GET /health`` reports status, version and the selected provider (never keys).
* ``GET /api/providers`` lists providers and whether each is configured.
* ``POST /api/review`` reviews a portfolio. Send JSON ``{"url": "...", "lang": "fa"}`` or a
  multipart form with ``url`` or ``file`` (a PDF), plus optional ``lang``, ``focus``,
  ``provider`` and ``model``. Returns the structured review as JSON.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .agent import Fanoos
from .cli import load_dotenv
from .errors import FanoosError, SourceError, bilingual
from .providers import PROVIDERS, preferred_provider_name
from .sources import is_url, load_source

ROOT = Path(os.environ.get("FANOOS_ROOT", Path(__file__).resolve().parent.parent))
WEB_DIR = ROOT / "web"
ASSETS_DIR = ROOT / "assets"
MAX_UPLOAD_BYTES = 15 * 1024 * 1024

AgentFactory = Callable[[str | None, str | None], Fanoos]


def default_agent_factory() -> AgentFactory:
    """FastAPI dependency returning a function that builds an agent (overridden in tests)."""
    return lambda provider, model: Fanoos(provider=provider, model=model)


def _private_host(url: str) -> bool:
    """Return ``True`` if ``url`` points at a loopback, private or link-local address.

    The server fetches user-supplied URLs, so it refuses internal addresses
    (set ``FANOOS_ALLOW_PRIVATE_URLS=1`` to allow them, for example for local testing).
    Hosts that do not resolve are allowed: the fetch then simply fails.
    """
    host = urlparse(url).hostname or ""
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError):
        return False
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
            return True
    return False


def _error(status: int, message: str, kind: str) -> JSONResponse:
    return JSONResponse({"error": message, "type": kind}, status_code=status)


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    load_dotenv()
    app = FastAPI(
        title="Fanoos API",
        version=__version__,
        description="Bilingual AI portfolio critic for UI/UX and web designers.",
    )

    if (WEB_DIR / "static").is_dir():
        app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    if ASSETS_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

    @app.exception_handler(FanoosError)
    async def fanoos_error_handler(request: Request, exc: FanoosError) -> JSONResponse:
        return _error(exc.http_status, str(exc), type(exc).__name__)

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html", media_type="text/html; charset=utf-8")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> FileResponse:
        return FileResponse(ASSETS_DIR / "favicon.svg", media_type="image/svg+xml")

    @app.get("/health")
    def health() -> dict[str, Any]:
        """Report that the server is up, and which provider would be used."""
        name = preferred_provider_name()
        return {
            "status": "ok",
            "version": __version__,
            "provider": name,
            "live_search": PROVIDERS[name].live_search if name else None,
        }

    @app.get("/api/providers")
    def providers() -> dict[str, Any]:
        """List providers and whether each one's key is set (keys are never returned)."""
        return {
            "selected": preferred_provider_name(),
            "providers": [
                {
                    "name": p.name,
                    "label": p.label,
                    "configured": p.configured,
                    "default_model": p.default_model,
                    "live_search": p.live_search,
                    "free_tier": p.free_tier,
                }
                for p in PROVIDERS.values()
            ],
        }

    @app.post("/api/review")
    async def review(request: Request, factory: AgentFactory = Depends(default_agent_factory)) -> JSONResponse:
        """Review a portfolio given as a URL (JSON or form) or an uploaded PDF (form field ``file``)."""
        fields, pdf = await _read_request(request)
        lang = fields.get("lang") or "fa"
        if lang not in ("fa", "en"):
            raise SourceError(bilingual("lang must be 'fa' or 'en'.", "زبان باید fa یا en باشد."))

        url = (fields.get("url") or "").strip()
        if not url and pdf is None:
            raise SourceError(
                bilingual(
                    "Send a portfolio URL (field 'url') or a PDF file (field 'file').",
                    "لینک پورتفولیو یا فایل PDF را بفرستید.",
                )
            )
        if url and not is_url(url):
            raise SourceError(
                bilingual("The URL must start with http:// or https://.", "لینک باید با https:// شروع شود.")
            )
        if url and pdf is None and not os.environ.get("FANOOS_ALLOW_PRIVATE_URLS") and _private_host(url):
            raise SourceError(
                bilingual("Private or local addresses cannot be reviewed.", "آدرس‌های داخلی یا محلی قابل بررسی نیستند.")
            )

        # Build the agent first so a missing key fails fast, before any download.
        agent = factory(fields.get("provider") or None, fields.get("model") or None)

        from starlette.concurrency import run_in_threadpool

        def run() -> dict[str, Any]:
            if pdf is not None:
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "portfolio.pdf"
                    path.write_bytes(pdf)
                    source = load_source(str(path))
            else:
                source = load_source(url)
            result = agent.review(source, lang, fields.get("focus") or None)  # type: ignore[arg-type]
            return result.to_dict(include_report=True)

        return JSONResponse(await run_in_threadpool(run))

    return app


async def _read_request(request: Request) -> tuple[dict[str, str], bytes | None]:
    """Return the text fields and the uploaded PDF bytes (if any) from a JSON or form request."""
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        try:
            body = await request.json()
        except ValueError as exc:
            raise SourceError(
                bilingual("The request body is not valid JSON.", "بدنه‌ی درخواست JSON معتبر نیست.")
            ) from exc
        if not isinstance(body, dict):
            raise SourceError(bilingual("Send a JSON object.", "یک شیء JSON بفرستید."))
        return {k: str(v) for k, v in body.items() if isinstance(v, (str, int, float))}, None

    form = await request.form()
    fields = {k: v for k, v in form.items() if isinstance(v, str)}
    upload = form.get("file")
    if upload is None or isinstance(upload, str) or not upload.filename:
        return fields, None

    data = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise _TooLarge()
    if not upload.filename.lower().endswith(".pdf") or not data.startswith(b"%PDF"):
        raise SourceError(bilingual("Only PDF files can be uploaded.", "فقط فایل PDF قابل بارگذاری است."))
    return fields, data


class _TooLarge(SourceError):
    http_status = 413

    def __init__(self) -> None:
        mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        super().__init__(bilingual(f"The PDF is larger than {mb} MB.", f"حجم PDF بیشتر از {mb} مگابایت است."))


app = create_app()

__all__ = ["app", "create_app", "default_agent_factory"]
