"""The :class:`Fanoos` agent: builds the request, streams the reply, parses it.

Fanoos talks to xAI's OpenAI-compatible Responses API. ``web_search`` and
``x_search`` are server-side Agent Tools, so the whole tool loop (the model
searching, reading results and searching again) happens inside one streamed
request; the client only has to read the text deltas as they arrive.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from typing import Any, Literal

from .errors import (
    APIError,
    AuthenticationFailedError,
    MissingAPIKeyError,
    NetworkError,
    RateLimitError,
)
from .review import Review, parse_review
from .sources import PortfolioSource
from .system_prompt import OUTPUT_FORMAT_INSTRUCTIONS, SYSTEM_PROMPT
from .tools import review_tools

DEFAULT_BASE_URL: str = "https://api.x.ai/v1"
DEFAULT_MODEL: str = "grok-4-1-fast-reasoning"
"""Grok 4.1 Fast (reasoning variant). Override with ``FANOOS_MODEL`` or ``--model``."""

API_KEY_ENV: str = "XAI_API_KEY"
MODEL_ENV: str = "FANOOS_MODEL"

Language = Literal["fa", "en"]

_REQUEST = {
    "fa": "لطفاً این پورتفولیو را بررسی کن. پاسخ را به فارسی بنویس و اصطلاحات طراحی را انگلیسی نگه دار.",
    "en": "Please review this portfolio. Write your review in English.",
}


def build_user_message(source: PortfolioSource, language: Language = "fa", focus: str | None = None) -> str:
    """Compose the user turn for a review request.

    Args:
        source: The portfolio to review.
        language: ``"fa"`` (default) or ``"en"``; the reply follows this language.
        focus: Optional extra request, such as "Focus on the Venture Compass case study".

    Returns:
        The message text.
    """
    parts = [_REQUEST[language]]
    if focus:
        parts.append(focus.strip())
    label = "Portfolio URL" if source.kind == "url" else "Portfolio PDF"
    parts.append(f"{label}: {source.location}")
    if source.note:
        parts.append(f"Note: {source.note}")
    if source.text:
        parts.append(f"Extracted portfolio content:\n<<<\n{source.text}\n>>>")
    return "\n\n".join(parts)


class Fanoos:
    """The Fanoos portfolio critic.

    Example:
        >>> from fanoos import Fanoos, load_source
        >>> review = Fanoos().review(load_source("https://example.com"))  # doctest: +SKIP
        >>> review.scores["narrative"]  # doctest: +SKIP
        72
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 300.0,
        max_retries: int = 2,
        client: Any | None = None,
    ) -> None:
        """Create an agent.

        The API key is read only from the ``XAI_API_KEY`` environment variable;
        it is never accepted as an argument, stored in the repository, or logged.

        Args:
            model: Model ID. Defaults to ``$FANOOS_MODEL`` or :data:`DEFAULT_MODEL`.
            base_url: OpenAI-compatible endpoint.
            timeout: Seconds to wait for the whole streamed response.
            max_retries: Automatic retries for transient errors.
            client: A pre-built OpenAI-compatible client (used in tests).

        Raises:
            MissingAPIKeyError: If no client is given and ``XAI_API_KEY`` is unset.
        """
        self.model = model or os.environ.get(MODEL_ENV) or DEFAULT_MODEL
        if client is None:
            api_key = os.environ.get(API_KEY_ENV, "").strip()
            if not api_key:
                raise MissingAPIKeyError()
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=max_retries)
        self._client = client

    def __repr__(self) -> str:  # never include the key
        return f"Fanoos(model={self.model!r})"

    def build_input(
        self, source: PortfolioSource, language: Language = "fa", focus: str | None = None
    ) -> list[dict[str, str]]:
        """Return the ``input`` messages for a review request.

        The persona is sent verbatim as the first system message; the output
        format comes second, so the persona itself is never altered.
        """
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": OUTPUT_FORMAT_INSTRUCTIONS},
            {"role": "user", "content": build_user_message(source, language, focus)},
        ]

    def stream(self, source: PortfolioSource, language: Language = "fa", focus: str | None = None) -> Iterator[str]:
        """Stream the review text as it is generated.

        Args:
            source: The portfolio to review.
            language: Reply language.
            focus: Optional extra request.

        Yields:
            Text fragments, in order.

        Raises:
            AuthenticationFailedError, RateLimitError, NetworkError, APIError:
                Translated from the underlying client's exceptions.
        """
        with _translate_errors():
            events = self._client.responses.create(
                model=self.model,
                input=self.build_input(source, language, focus),
                tools=review_tools(),
                stream=True,
            )
            for event in events:
                kind = getattr(event, "type", "")
                if kind == "response.output_text.delta":
                    yield event.delta
                elif kind in ("response.failed", "error"):
                    raise APIError(f"The model stopped with an error: {_event_error(event)}")

    def review(
        self,
        source: PortfolioSource,
        language: Language = "fa",
        focus: str | None = None,
        on_delta: Callable[[str], None] | None = None,
    ) -> Review:
        """Run a full review and return it parsed.

        Args:
            source: The portfolio to review.
            language: Reply language.
            focus: Optional extra request.
            on_delta: Called with each text fragment while streaming.

        Returns:
            The structured :class:`~fanoos.review.Review`.

        Raises:
            MalformedOutputError: If the reply cannot be parsed.
        """
        chunks: list[str] = []
        for delta in self.stream(source, language, focus):
            chunks.append(delta)
            if on_delta is not None:
                on_delta(delta)
        return parse_review("".join(chunks))


def _event_error(event: Any) -> str:
    error = getattr(event, "error", None) or getattr(getattr(event, "response", None), "error", None)
    return str(getattr(error, "message", None) or error or "unknown error")


class _translate_errors:
    """Context manager mapping ``openai`` exceptions to Fanoos errors."""

    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any) -> bool:
        if exc is None:
            return False
        try:
            import openai
        except ImportError:  # pragma: no cover - openai is a hard dependency
            return False

        if isinstance(exc, openai.RateLimitError):
            headers = getattr(getattr(exc, "response", None), "headers", None) or {}
            raise RateLimitError(headers.get("retry-after")) from exc
        if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
            raise AuthenticationFailedError() from exc
        if isinstance(exc, (openai.APITimeoutError, openai.APIConnectionError)):
            raise NetworkError(
                "Could not reach the xAI API (api.x.ai). Check your internet connection, VPN or proxy, then try again."
            ) from exc
        if isinstance(exc, openai.NotFoundError):
            raise APIError(
                "The xAI API returned 404. The model ID may be wrong: set FANOOS_MODEL "
                "or pass --model with a model listed at https://docs.x.ai/docs/models."
            ) from exc
        if isinstance(exc, openai.APIStatusError):
            raise APIError(f"The xAI API returned HTTP {exc.status_code}: {_short(exc)}") from exc
        if isinstance(exc, openai.APIError):
            raise APIError(f"xAI API error: {_short(exc)}") from exc
        return False


def _short(exc: BaseException, limit: int = 300) -> str:
    text = str(getattr(exc, "message", None) or exc)
    return text if len(text) <= limit else text[:limit] + "…"


__all__ = ["Fanoos", "DEFAULT_MODEL", "DEFAULT_BASE_URL", "API_KEY_ENV", "MODEL_ENV", "build_user_message"]
