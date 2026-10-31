"""FastAPI server: the web UI plus a JSON API for reviews.

Run it locally from the repository root::

    uvicorn server:app --reload

On cPanel / Passenger the same app is served through ``passenger_wsgi.py``.

Endpoints:

* ``GET /`` serves ``web/index.html``; ``/static`` and ``/assets`` serve the UI files and logos.
* ``GET /health`` is a liveness check: status, version and whether an AI provider is configured.
* ``GET /api/providers`` lists providers and whether each is configured (never keys).
* ``POST /api/review`` reviews a portfolio. Send JSON ``{"url": "...", "lang": "fa"}`` or a
  multipart form with ``url`` or ``file`` (a PDF), plus optional ``lang`` and ``focus``.

Production safeguards (see :mod:`fanoos.settings`): SSRF-safe URL fetching, a request body
limit enforced while the body streams in, a per-IP rate limit and a concurrency cap (so the
AI quota cannot be drained), security headers with a strict Content-Security-Policy, secret
redaction in every error, and a generic error handler that never leaks internals.
"""

from __future__ import annotations

import asyncio
import base64
import dataclasses
import hashlib
import logging
import os
import re
import tempfile
import threading
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import __version__
from .agent import Fanoos
from .errors import FanoosError, SourceError, bilingual, redact
from .netguard import check_url
from .providers import PROVIDERS, preferred_provider_name
from .settings import Settings, load_dotenv, load_settings
from .sources import is_url, load_source

ROOT = Path(os.environ.get("FANOOS_ROOT", Path(__file__).resolve().parent.parent))
WEB_DIR = ROOT / "web"
ASSETS_DIR = ROOT / "assets"
MAX_FIELD_CHARS = 2000

log = logging.getLogger("fanoos")

AgentFactory = Callable[[str | None, str | None], Fanoos]


def default_agent_factory() -> AgentFactory:
    """FastAPI dependency returning a function that builds an agent (overridden in tests)."""
    return lambda provider, model: Fanoos(provider=provider, model=model, timeout=load_settings().timeout)


def _error(status: int, message: str, kind: str, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse({"error": redact(message), "type": kind}, status_code=status, headers=headers)


class TooLargeError(SourceError):
    """The request body or uploaded file exceeds the configured limit."""

    http_status = 413

    def __init__(self, limit: int) -> None:
        mb = max(1, limit // (1024 * 1024))
        super().__init__(bilingual(f"The upload is larger than {mb} MB.", f"حجم فایل بیشتر از {mb} مگابایت است."))


class RateLimitedError(FanoosError):
    """Too many reviews from one client."""

    http_status = 429

    def __init__(self, retry_after: int) -> None:
        super().__init__(
            bilingual(
                f"Too many reviews from your connection. Try again in {retry_after} seconds.",
                "تعداد درخواست‌های شما زیاد بوده است. کمی بعد دوباره امتحان کنید.",
            )
        )
        self.retry_after = retry_after


class BusyError(FanoosError):
    """All review slots are in use."""

    http_status = 503

    def __init__(self) -> None:
        super().__init__(
            bilingual(
                "Fanoos is busy with other reviews. Please try again in a minute.",
                "فانوس مشغول بررسی‌های دیگر است. یک دقیقه‌ی دیگر دوباره امتحان کنید.",
            )
        )


class RateLimiter:
    """Sliding-window limiter per client key (in memory, per process)."""

    def __init__(self, limit: int, window: int) -> None:
        self.limit, self.window = limit, window
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Record a hit for ``key`` or raise :class:`RateLimitedError`."""
        if self.limit <= 0:
            return
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                raise RateLimitedError(int(self.window - (now - hits[0])) + 1)
            hits.append(now)
            if len(self._hits) > 10_000:  # bound memory: drop idle clients
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] > self.window]:
                    self._hits.pop(k, None)


class BodyLimitMiddleware:
    """Reject request bodies larger than ``limit`` while they stream in (before spooling to disk)."""

    def __init__(self, app: ASGIApp, limit: int) -> None:
        self.app, self.limit = app, limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        declared = headers.get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.limit:
            await _error(413, str(TooLargeError(self.limit)), "TooLargeError")(scope, receive, send)
            return
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.limit:
                    raise TooLargeError(self.limit)
            return message

        await self.app(scope, limited_receive, send)


def _importmap_hash(index: Path) -> str | None:
    """CSP hash of the inline import map in ``index.html`` (the only inline script)."""
    try:
        html = index.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r'<script type="importmap">(.*?)</script>', html, re.S)
    if not match:
        return None
    digest = hashlib.sha256(match.group(1).encode("utf-8")).digest()
    return "'sha256-" + base64.b64encode(digest).decode() + "'"


def security_headers(importmap_hash: str | None) -> dict[str, str]:
    """Headers added to every response."""
    script_src = "'self'" + (f" {importmap_hash}" if importmap_hash else "")
    csp = "; ".join(
        [
            "default-src 'self'",
            f"script-src {script_src}",
            "style-src 'self' 'unsafe-inline'",  # inline style attributes carry animation delays
            "img-src 'self' data:",
            "font-src 'self'",
            "connect-src 'self'",
            "object-src 'none'",
            "base-uri 'none'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        ]
    )
    return {
        "Content-Security-Policy": csp,
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
        "Cross-Origin-Opener-Policy": "same-origin",
    }


def _client_ip(request: Request, trust_proxy: bool) -> str:
    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _safe_filename(name: str | None) -> str:
    stem = re.sub(r"[^\w.\- ]+", "_", Path(name or "portfolio.pdf").name)[:80].strip() or "portfolio.pdf"
    return stem if stem.lower().endswith(".pdf") else stem + ".pdf"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application."""
    load_dotenv(ROOT / ".env")
    settings = settings or load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO), format="%(levelname)s %(name)s: %(message)s"
    )

    docs = {} if not settings.production else {"docs_url": None, "redoc_url": None, "openapi_url": None}
    app = FastAPI(
        title="Fanoos API",
        version=__version__,
        description="Bilingual AI portfolio critic for UI/UX and web designers.",
        debug=False,
        **docs,
    )
    app.state.settings = settings
    limiter = RateLimiter(*settings.rate_limit)
    slots = asyncio.Semaphore(settings.max_concurrent)
    headers = security_headers(_importmap_hash(WEB_DIR / "index.html"))

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: Callable[..., Any]) -> Any:
        response = await call_next(request)
        for key, value in headers.items():
            response.headers.setdefault(key, value)
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        if request.url.scheme == "https" or (settings.trust_proxy and forwarded_proto == "https"):
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    app.add_middleware(BodyLimitMiddleware, limit=settings.max_upload_bytes + 64 * 1024)

    if (WEB_DIR / "static").is_dir():
        app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    if ASSETS_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

    @app.exception_handler(FanoosError)
    async def fanoos_error_handler(request: Request, exc: FanoosError) -> JSONResponse:
        extra = {"Retry-After": str(exc.retry_after)} if getattr(exc, "retry_after", None) else None
        if exc.http_status >= 500:
            log.warning("%s on %s: %s", type(exc).__name__, request.url.path, redact(str(exc)).splitlines()[0])
        return _error(exc.http_status, str(exc), type(exc).__name__, extra)

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        log.error("Unhandled error on %s: %s", request.url.path, redact(repr(exc)))
        return _error(
            500,
            bilingual(
                "Something went wrong on the server. Please try again.", "خطایی در سرور رخ داد. دوباره امتحان کنید."
            ),
            "InternalError",
        )

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html", media_type="text/html; charset=utf-8")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> FileResponse:
        return FileResponse(ASSETS_DIR / "favicon.svg", media_type="image/svg+xml")

    @app.get("/health")
    def health() -> dict[str, Any]:
        """Liveness check. Says whether a provider is configured; never returns keys or settings."""
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
        fields, pdf, pdf_name = await _read_request(request, settings.max_upload_bytes)
        lang = fields.get("lang") or "fa"
        if lang not in ("fa", "en"):
            raise SourceError(bilingual("lang must be 'fa' or 'en'.", "زبان باید fa یا en باشد."))
        focus = (fields.get("focus") or "").strip()[:500] or None

        url = (fields.get("url") or "").strip()
        if not url and pdf is None:
            raise SourceError(
                bilingual(
                    "Send a portfolio URL (field 'url') or a PDF file (field 'file').",
                    "لینک پورتفولیو یا فایل PDF را بفرستید.",
                )
            )
        if url and pdf is None:
            if not is_url(url) or len(url) > MAX_FIELD_CHARS:
                raise SourceError(
                    bilingual("The URL must start with http:// or https://.", "لینک باید با https:// شروع شود.")
                )
            from starlette.concurrency import run_in_threadpool

            await run_in_threadpool(check_url, url, allow_private=settings.allow_private_urls)

        # In production the provider and model come only from the server's environment, so a
        # visitor cannot switch to a more expensive model.
        provider = None if settings.production else (fields.get("provider") or None)
        model = None if settings.production else (fields.get("model") or None)
        agent = factory(provider, model)  # fails fast on a missing key, before any download

        limiter.check(_client_ip(request, settings.trust_proxy))
        if slots.locked():
            raise BusyError()

        from starlette.concurrency import run_in_threadpool

        def run() -> dict[str, Any]:
            if pdf is not None:
                with tempfile.TemporaryDirectory(prefix="fanoos-") as tmp:
                    path = Path(tmp) / "upload.pdf"
                    path.write_bytes(pdf)
                    source = load_source(str(path))
                # The model sees the visitor's file name, never a server path.
                source = dataclasses.replace(source, location=pdf_name)
            else:
                source = load_source(url, allow_private=settings.allow_private_urls)
            result = agent.review(source, lang, focus)  # type: ignore[arg-type]
            return result.to_dict(include_report=True)

        async with slots:
            started = time.monotonic()
            data = await run_in_threadpool(run)
            log.info(
                "review ok: %s via %s in %.1fs",
                "pdf" if pdf is not None else "url",
                data.get("provider"),
                time.monotonic() - started,
            )
        return JSONResponse(data)

    return app


async def _read_request(request: Request, max_bytes: int) -> tuple[dict[str, str], bytes | None, str]:
    """Return text fields, uploaded PDF bytes (if any) and its safe file name, from JSON or a form."""
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
        return {k: str(v)[:MAX_FIELD_CHARS] for k, v in body.items() if isinstance(v, (str, int, float))}, None, ""

    if not content_type.startswith("multipart/form-data") and not content_type.startswith(
        "application/x-www-form-urlencoded"
    ):
        raise SourceError(bilingual("Send JSON or a form.", "درخواست را به صورت JSON یا فرم بفرستید."))
    form = await request.form(max_files=1, max_fields=20)
    fields = {k: v[:MAX_FIELD_CHARS] for k, v in form.items() if isinstance(v, str)}
    upload = form.get("file")
    if upload is None or isinstance(upload, str) or not upload.filename:
        return fields, None, ""

    data = await upload.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise TooLargeError(max_bytes)
    if not upload.filename.lower().endswith(".pdf") or not data.startswith(b"%PDF"):
        raise SourceError(bilingual("Only PDF files can be uploaded.", "فقط فایل PDF قابل بارگذاری است."))
    return fields, data, _safe_filename(upload.filename)


app = create_app()

__all__ = ["app", "create_app", "default_agent_factory", "RateLimiter", "security_headers"]
