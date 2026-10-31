"""Exceptions raised by Fanoos.

Every error carries a short, human-readable message that the CLI prints as-is,
so messages say what went wrong *and* what to do about it.
"""

from __future__ import annotations


class FanoosError(Exception):
    """Base class for every error Fanoos raises on purpose."""

    exit_code: int = 1


class MissingAPIKeyError(FanoosError):
    """``XAI_API_KEY`` is not set in the environment."""

    exit_code = 2

    def __init__(self) -> None:
        super().__init__(
            "XAI_API_KEY is not set.\n"
            "Create a key at https://console.x.ai, then export it:\n"
            "  macOS/Linux:  export XAI_API_KEY=xai-...\n"
            '  Windows (PowerShell):  $env:XAI_API_KEY = "xai-..."\n'
            "or copy .env.example to .env and fill it in."
        )


class AuthenticationFailedError(FanoosError):
    """The xAI API rejected the key."""

    exit_code = 2

    def __init__(self) -> None:
        super().__init__(
            "The xAI API rejected your key (401/403). Check that XAI_API_KEY is "
            "correct and still active at https://console.x.ai."
        )


class NetworkError(FanoosError):
    """The API (or the portfolio URL) could not be reached."""

    exit_code = 3


class RateLimitError(FanoosError):
    """The xAI API answered 429 Too Many Requests."""

    exit_code = 4

    def __init__(self, retry_after: str | None = None) -> None:
        hint = f" Try again in {retry_after} seconds." if retry_after else " Wait a minute and try again."
        super().__init__("Rate limit reached (HTTP 429): too many requests or tokens for your xAI plan." + hint)
        self.retry_after = retry_after


class APIError(FanoosError):
    """Any other error status returned by the xAI API."""

    exit_code = 5


class MalformedOutputError(FanoosError):
    """The model's reply could not be turned into a :class:`~fanoos.review.Review`."""

    exit_code = 6


class SourceError(FanoosError):
    """The portfolio input (URL or PDF path) could not be read."""

    exit_code = 7


__all__ = [
    "FanoosError",
    "MissingAPIKeyError",
    "AuthenticationFailedError",
    "NetworkError",
    "RateLimitError",
    "APIError",
    "MalformedOutputError",
    "SourceError",
]
