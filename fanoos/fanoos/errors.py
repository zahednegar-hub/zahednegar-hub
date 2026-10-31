"""Exceptions raised by Fanoos.

Every error carries a short, human-readable message that the CLI and the web
API show as-is. Messages are bilingual (English, then Persian) and say what
went wrong *and* what to do about it.
"""

from __future__ import annotations

import os
import re


def bilingual(en: str, fa: str) -> str:
    """Join an English and a Persian message on separate lines."""
    return f"{en}\n{fa}"


_KEY_ENV_VARS = ("XAI_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY")
_KEY_PATTERNS = re.compile(r"(xai-[A-Za-z0-9]{8,}|AIza[0-9A-Za-z_\-]{20,}|gsk_[A-Za-z0-9]{10,}|sk-[A-Za-z0-9_\-]{16,})")


def redact(text: str) -> str:
    """Remove API keys from ``text``: the configured key values and anything shaped like a key.

    Used on every error message before it is shown or logged, so a provider that echoes a
    key back can never leak it.
    """
    for var in _KEY_ENV_VARS:
        value = os.environ.get(var, "").strip()
        if len(value) >= 8:
            text = text.replace(value, "[redacted]")
    return _KEY_PATTERNS.sub("[redacted]", text)


class FanoosError(Exception):
    """Base class for every error Fanoos raises on purpose."""

    exit_code: int = 1
    http_status: int = 500


class MissingAPIKeyError(FanoosError):
    """The selected provider's API key is not set (or no provider is configured at all)."""

    exit_code = 2
    http_status = 503

    def __init__(self, env_var: str | None = None, signup_url: str | None = None) -> None:
        if env_var is None:
            super().__init__(
                bilingual(
                    "No AI provider is configured. Set one of XAI_API_KEY, GEMINI_API_KEY (free) "
                    "or GROQ_API_KEY (free), or copy .env.example to .env and fill it in. "
                    "Run `fanoos providers` to check.",
                    "هیچ ارائه‌دهنده‌ی هوش مصنوعی تنظیم نشده. یکی از کلیدهای XAI_API_KEY، "
                    "GEMINI_API_KEY (رایگان) یا GROQ_API_KEY (رایگان) را تنظیم کنید.",
                )
            )
        else:
            where = f" Get one at {signup_url}." if signup_url else ""
            super().__init__(
                bilingual(
                    f"{env_var} is not set.{where} Then export it "
                    f'(macOS/Linux: export {env_var}=...  ·  Windows PowerShell: $env:{env_var} = "...") '
                    "or put it in .env.",
                    f"کلید {env_var} تنظیم نشده. آن را در متغیر محیطی یا فایل ‎.env‎ قرار دهید.",
                )
            )
        self.env_var = env_var


class UnknownProviderError(FanoosError):
    """``FANOOS_PROVIDER`` (or ``--provider``) names a provider Fanoos does not know."""

    exit_code = 2
    http_status = 400

    def __init__(self, name: str, known: list[str]) -> None:
        options = ", ".join(known)
        super().__init__(
            bilingual(
                f"Unknown provider '{name}'. Choose one of: {options}.",
                f"ارائه‌دهنده‌ی «{name}» شناخته نشد. یکی از این‌ها را انتخاب کنید: {options}",
            )
        )


class AuthenticationFailedError(FanoosError):
    """The provider rejected the API key."""

    exit_code = 2
    http_status = 502

    def __init__(self, provider: str = "xAI", env_var: str = "XAI_API_KEY") -> None:
        super().__init__(
            bilingual(
                f"{provider} rejected your API key. Check that {env_var} is correct and still active.",
                f"{provider} کلید API شما را نپذیرفت. درستی و فعال بودن {env_var} را بررسی کنید.",
            )
        )


class NetworkError(FanoosError):
    """The API (or the portfolio URL) could not be reached."""

    exit_code = 3
    http_status = 504


class RateLimitError(FanoosError):
    """The provider answered 429 Too Many Requests, even after automatic retries."""

    exit_code = 4
    http_status = 429

    def __init__(self, provider: str = "xAI", retry_after: str | None = None) -> None:
        wait = f"{retry_after} seconds" if retry_after else "a minute"
        super().__init__(
            bilingual(
                f"{provider} rate limit reached (HTTP 429), even after automatic retries. "
                f"Free tiers allow a limited number of requests per minute and per day. Try again in {wait}.",
                f"سقف درخواست {provider} پر شده (HTTP 429). سهمیه‌ی رایگان محدود است؛ کمی بعد دوباره امتحان کنید.",
            )
        )
        self.retry_after = retry_after


class APIError(FanoosError):
    """Any other error returned by the provider."""

    exit_code = 5
    http_status = 502


class MalformedOutputError(FanoosError):
    """The model's reply could not be turned into a :class:`~fanoos.review.Review`."""

    exit_code = 6
    http_status = 502


class SourceError(FanoosError):
    """The portfolio input (URL or PDF path) could not be read."""

    exit_code = 7
    http_status = 400


__all__ = [
    "bilingual",
    "redact",
    "FanoosError",
    "MissingAPIKeyError",
    "UnknownProviderError",
    "AuthenticationFailedError",
    "NetworkError",
    "RateLimitError",
    "APIError",
    "MalformedOutputError",
    "SourceError",
]
