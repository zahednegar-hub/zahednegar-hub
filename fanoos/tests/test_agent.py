"""Tests for fanoos.agent with a fake OpenAI-compatible client."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import openai
import pytest

from fanoos.agent import DEFAULT_MODEL, Fanoos, build_user_message
from fanoos.errors import APIError, AuthenticationFailedError, MissingAPIKeyError, NetworkError, RateLimitError
from fanoos.sources import PortfolioSource
from fanoos.system_prompt import SYSTEM_PROMPT

from .conftest import FakeClient, text_events

SOURCE = PortfolioSource("url", "https://example.com", "Title: Example\n\nHello")
REQUEST = httpx.Request("POST", "https://api.x.ai/v1/responses")


def _status_error(cls: type[openai.APIStatusError], status: int, headers: dict | None = None) -> openai.APIStatusError:
    return cls("boom", response=httpx.Response(status, request=REQUEST, headers=headers), body=None)


def test_missing_api_key_raises() -> None:
    with pytest.raises(MissingAPIKeyError, match="XAI_API_KEY"):
        Fanoos()


def test_key_is_read_from_env_and_never_shown(monkeypatch) -> None:
    monkeypatch.setenv("XAI_API_KEY", "test-secret-value")
    agent = Fanoos()
    assert "test-secret-value" not in repr(agent)
    assert agent.model == DEFAULT_MODEL


def test_model_from_env(monkeypatch) -> None:
    monkeypatch.setenv("FANOOS_MODEL", "grok-test")
    assert Fanoos(client=FakeClient()).model == "grok-test"


def test_request_shape(sample_reply: str) -> None:
    client = FakeClient(text_events(sample_reply))
    review = Fanoos(client=client, model="m").review(SOURCE, language="en", focus="Focus on case studies")
    call = client.responses.calls[0]
    assert call["model"] == "m"
    assert call["stream"] is True
    assert call["tools"] == [{"type": "web_search"}, {"type": "x_search"}]
    assert call["input"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    user = call["input"][-1]["content"]
    assert "https://example.com" in user and "Focus on case studies" in user and "Hello" in user
    assert review.scores["narrative"] == 62


def test_on_delta_receives_stream(sample_reply: str) -> None:
    seen: list[str] = []
    Fanoos(client=FakeClient(text_events(sample_reply))).review(SOURCE, on_delta=seen.append)
    assert "".join(seen) == sample_reply


def test_failed_event_raises() -> None:
    events = [SimpleNamespace(type="response.failed", response=SimpleNamespace(error=SimpleNamespace(message="bad")))]
    with pytest.raises(APIError, match="bad"):
        list(Fanoos(client=FakeClient(events)).stream(SOURCE))


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (_status_error(openai.RateLimitError, 429, {"retry-after": "12"}), RateLimitError),
        (_status_error(openai.AuthenticationError, 401), AuthenticationFailedError),
        (_status_error(openai.NotFoundError, 404), APIError),
        (_status_error(openai.InternalServerError, 500), APIError),
        (openai.APIConnectionError(request=REQUEST), NetworkError),
        (openai.APITimeoutError(request=REQUEST), NetworkError),
    ],
)
def test_errors_are_translated(error: Exception, expected: type[Exception]) -> None:
    with pytest.raises(expected):
        list(Fanoos(client=FakeClient(error=error)).stream(SOURCE))


def test_rate_limit_mentions_retry_after() -> None:
    with pytest.raises(RateLimitError, match="12 seconds"):
        list(
            Fanoos(client=FakeClient(error=_status_error(openai.RateLimitError, 429, {"retry-after": "12"}))).stream(
                SOURCE
            )
        )


def test_persian_is_default_language() -> None:
    assert "فارسی" in build_user_message(SOURCE)
    assert "English" in build_user_message(SOURCE, "en")
