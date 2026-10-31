"""The :class:`Fanoos` agent: builds the request, streams the reply, parses it.

Fanoos is provider-agnostic (see :mod:`fanoos.providers`). On xAI it uses the
Responses API with the server-side Agent Tools ``web_search`` and ``x_search``:
the whole tool loop runs inside one streamed request. On the free providers
(Gemini, Groq) it uses streamed Chat Completions with the same persona and
output format, and no live search.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from typing import Any, Literal

from .errors import (
    APIError,
    AuthenticationFailedError,
    NetworkError,
    RateLimitError,
    bilingual,
)
from .providers import MODEL_ENV, PROVIDERS, XAI, Provider, get_provider, select_provider
from .review import Review, parse_review
from .sources import PortfolioSource
from .system_prompt import (
    NO_LIVE_SEARCH_FOOTER,
    NO_LIVE_SEARCH_INSTRUCTIONS,
    OUTPUT_FORMAT_INSTRUCTIONS,
    SYSTEM_PROMPT,
)
from .tools import review_tools

DEFAULT_MODEL: str = XAI.default_model
"""Default model of the default provider (kept for backwards compatibility)."""

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


def build_system_prompt(live_search: bool) -> str:
    """Return the full system message: the persona verbatim, followed only by appended instructions."""
    parts = [SYSTEM_PROMPT, OUTPUT_FORMAT_INSTRUCTIONS]
    if not live_search:
        parts.append(NO_LIVE_SEARCH_INSTRUCTIONS)
    return "\n\n".join(p.strip() for p in parts) + "\n"


class Fanoos:
    """The Fanoos portfolio critic.

    Example:
        >>> from fanoos import Fanoos, load_source
        >>> agent = Fanoos(provider="gemini")  # doctest: +SKIP
        >>> review = agent.review(load_source("https://example.com"))  # doctest: +SKIP
        >>> review.scores["narrative"]  # doctest: +SKIP
        72
    """

    def __init__(
        self,
        *,
        provider: str | Provider | None = None,
        model: str | None = None,
        timeout: float = 300.0,
        max_retries: int = 3,
        client: Any | None = None,
    ) -> None:
        """Create an agent.

        API keys are read only from the environment (``XAI_API_KEY``,
        ``GEMINI_API_KEY``, ``GROQ_API_KEY``); they are never accepted as
        arguments, stored, or logged.

        Args:
            provider: Provider name or object. Defaults to ``$FANOOS_PROVIDER``,
                then the first configured provider (xai, gemini, groq).
            model: Model ID. Defaults to ``$FANOOS_MODEL``, then the provider's default.
            timeout: Seconds to wait for the whole streamed response.
            max_retries: Automatic retries (with backoff) for 429s and transient errors.
            client: A pre-built OpenAI-compatible client (used in tests). The
                provider then defaults to xai and no key is needed.

        Raises:
            UnknownProviderError: If ``provider`` is not a known name.
            MissingAPIKeyError: If the selected provider has no key.
        """
        if isinstance(provider, Provider):
            self.provider = provider
        elif client is not None:
            self.provider = get_provider(provider) if provider else XAI
        else:
            self.provider = select_provider(provider)
        self.model = model or os.environ.get(MODEL_ENV, "").strip() or self.provider.default_model

        if client is None:
            from openai import OpenAI

            client = OpenAI(
                api_key=self.provider.api_key(),
                base_url=self.provider.base_url,
                timeout=timeout,
                max_retries=max_retries,
            )
        self._client = client

    def __repr__(self) -> str:  # never include the key
        return f"Fanoos(provider={self.provider.name!r}, model={self.model!r})"

    @property
    def live_search(self) -> bool:
        """Whether this agent's provider can search the web and X during a review."""
        return self.provider.live_search

    def build_messages(
        self, source: PortfolioSource, language: Language = "fa", focus: str | None = None
    ) -> list[dict[str, str]]:
        """Return the messages for a review request (one system message, one user message)."""
        return [
            {"role": "system", "content": build_system_prompt(self.live_search)},
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
        messages = self.build_messages(source, language, focus)
        with _translate_errors(self.provider):
            if self.live_search:
                yield from self._stream_responses(messages)
            else:
                yield from self._stream_chat(messages)

    def _stream_responses(self, messages: list[dict[str, str]]) -> Iterator[str]:
        events = self._client.responses.create(model=self.model, input=messages, tools=review_tools(), stream=True)
        for event in events:
            kind = getattr(event, "type", "")
            if kind == "response.output_text.delta":
                yield event.delta
            elif kind in ("response.failed", "error"):
                raise APIError(f"The model stopped with an error: {_event_error(event)}")

    def _stream_chat(self, messages: list[dict[str, str]]) -> Iterator[str]:
        chunks = self._client.chat.completions.create(model=self.model, messages=messages, stream=True)
        for chunk in chunks:
            for choice in getattr(chunk, "choices", None) or []:
                text = getattr(getattr(choice, "delta", None), "content", None)
                if text:
                    yield text

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
            The structured :class:`~fanoos.review.Review`, tagged with the
            provider, model and whether live search was used.

        Raises:
            MalformedOutputError: If the reply cannot be parsed.
        """
        chunks: list[str] = []
        for delta in self.stream(source, language, focus):
            chunks.append(delta)
            if on_delta is not None:
                on_delta(delta)
        return self.finish("".join(chunks))

    def finish(self, text: str) -> Review:
        """Parse a complete reply and attach provider metadata (and the offline footer if needed)."""
        review = parse_review(text)
        review.provider = self.provider.name
        review.model = self.model
        review.live_search = self.live_search
        if not self.live_search and NO_LIVE_SEARCH_FOOTER not in review.report:
            review.report = f"{review.report}\n\n{NO_LIVE_SEARCH_FOOTER}".strip()
        return review


def _event_error(event: Any) -> str:
    error = getattr(event, "error", None) or getattr(getattr(event, "response", None), "error", None)
    return str(getattr(error, "message", None) or error or "unknown error")


class _translate_errors:
    """Context manager mapping ``openai`` exceptions to Fanoos errors."""

    def __init__(self, provider: Provider) -> None:
        self.provider = provider

    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any) -> bool:
        if exc is None:
            return False
        import openai

        p = self.provider
        if isinstance(exc, openai.RateLimitError):
            headers = getattr(getattr(exc, "response", None), "headers", None) or {}
            raise RateLimitError(p.label, headers.get("retry-after")) from exc
        if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)) or (
            isinstance(exc, openai.BadRequestError) and "api key" in _short(exc).lower()
        ):
            raise AuthenticationFailedError(p.label, p.env_var) from exc
        if isinstance(exc, (openai.APITimeoutError, openai.APIConnectionError)):
            host = p.base_url.split("/")[2]
            raise NetworkError(
                bilingual(
                    f"Could not reach {p.label} ({host}). Check your connection, VPN or proxy, then try again.",
                    f"اتصال به {p.label} برقرار نشد. اینترنت، VPN یا پروکسی را بررسی کنید و دوباره امتحان کنید.",
                )
            ) from exc
        if isinstance(exc, openai.NotFoundError):
            raise APIError(
                bilingual(
                    f"{p.label} returned 404: the model '{_exc_model(exc)}' may not exist or may be retired. "
                    "Set FANOOS_MODEL or pass --model with a current model ID.",
                    f"{p.label} مدل را پیدا نکرد (404). شناسه‌ی مدل را با FANOOS_MODEL یا ‎--model‎ عوض کنید.",
                )
            ) from exc
        if isinstance(exc, openai.APIStatusError):
            raise APIError(f"{p.label} returned HTTP {exc.status_code}: {_short(exc)}") from exc
        if isinstance(exc, openai.APIError):
            raise APIError(f"{p.label} API error: {_short(exc)}") from exc
        return False


def _exc_model(exc: BaseException) -> str:
    """Best-effort model name from a failed request, for error messages."""
    request = getattr(exc, "request", None)
    try:
        import json

        return str(json.loads(request.content).get("model", "?")) if request is not None else "?"
    except (ValueError, AttributeError, TypeError):
        return "?"


def _short(exc: BaseException, limit: int = 300) -> str:
    """Return the provider's own error message (unwrapping list-shaped bodies such as Gemini's)."""
    body: Any = getattr(exc, "body", None)
    if isinstance(body, list) and body:
        body = body[0]
    text = ""
    if isinstance(body, dict):
        error = body.get("error", body)
        text = str(error.get("message", "")) if isinstance(error, dict) else str(error)
    text = text or str(getattr(exc, "message", None) or exc)
    return text if len(text) <= limit else text[:limit] + "…"


__all__ = ["Fanoos", "DEFAULT_MODEL", "PROVIDERS", "build_user_message", "build_system_prompt"]
