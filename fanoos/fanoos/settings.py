"""Runtime settings for the web server, read from environment variables.

Every value has a production-safe default, so a bare deployment is locked down;
loosen them only on purpose. API keys are *not* settings: they are read by
:mod:`fanoos.providers` straight from the environment and never stored here.

| Variable | Default | Meaning |
|---|---|---|
| ``FANOOS_ENV`` | ``production`` | ``development`` enables ``/docs`` |
| ``FANOOS_RATE_LIMIT`` | ``10/hour`` | Reviews per client IP (``N/second\\|minute\\|hour\\|day``; ``0`` = off) |
| ``FANOOS_MAX_CONCURRENT`` | ``2`` | Reviews processed at once per process |
| ``FANOOS_TIMEOUT`` | ``180`` | Seconds to wait for the AI provider |
| ``FANOOS_MAX_UPLOAD_MB`` | ``15`` | Largest accepted PDF |
| ``FANOOS_ALLOW_PRIVATE_URLS`` | off | Allow local/private URLs (never in production) |
| ``FANOOS_TRUST_PROXY`` | off | Take the client IP from ``X-Forwarded-For`` |
| ``FANOOS_LOG_LEVEL`` | ``INFO`` | Python logging level |
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

_UNITS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int, minimum: int = 0) -> int:
    try:
        return max(minimum, int(os.environ.get(name, "").strip() or default))
    except ValueError:
        return default


def parse_rate(value: str) -> tuple[int, int]:
    """Parse ``"10/hour"`` into ``(10, 3600)``. ``"0"`` or ``"off"`` disables limiting: ``(0, 0)``."""
    value = (value or "").strip().lower()
    if value in ("", "0", "off", "none"):
        return 0, 0
    match = re.fullmatch(r"(\d+)\s*/\s*(second|minute|hour|day)s?", value)
    if not match:
        raise ValueError(f"FANOOS_RATE_LIMIT must look like '10/hour', got {value!r}")
    return int(match.group(1)), _UNITS[match.group(2)]


@dataclass(frozen=True)
class Settings:
    """Server settings. Build with :func:`load_settings`."""

    env: str
    rate_limit: tuple[int, int]
    max_concurrent: int
    timeout: float
    max_upload_bytes: int
    allow_private_urls: bool
    trust_proxy: bool
    log_level: str

    @property
    def production(self) -> bool:
        """Whether this is a production deployment (the default)."""
        return self.env != "development"


def load_settings() -> Settings:
    """Read :class:`Settings` from the environment."""
    return Settings(
        env=os.environ.get("FANOOS_ENV", "production").strip().lower() or "production",
        rate_limit=parse_rate(os.environ.get("FANOOS_RATE_LIMIT", "10/hour")),
        max_concurrent=_int("FANOOS_MAX_CONCURRENT", 2, minimum=1),
        timeout=float(_int("FANOOS_TIMEOUT", 180, minimum=10)),
        max_upload_bytes=_int("FANOOS_MAX_UPLOAD_MB", 15, minimum=1) * 1024 * 1024,
        allow_private_urls=_flag("FANOOS_ALLOW_PRIVATE_URLS"),
        trust_proxy=_flag("FANOOS_TRUST_PROXY"),
        log_level=os.environ.get("FANOOS_LOG_LEVEL", "INFO").strip().upper() or "INFO",
    )


def load_dotenv(path: Path | None = None) -> None:
    """Load ``KEY=value`` lines from a ``.env`` file without overriding the real environment.

    Values are never printed or logged.

    Args:
        path: File to read; defaults to ``./.env``.
    """
    path = path or Path.cwd() / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


__all__ = ["Settings", "load_settings", "parse_rate", "load_dotenv"]
