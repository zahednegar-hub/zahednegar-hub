"""Tests for provider selection and the free-provider (no live search) path."""

from __future__ import annotations

import httpx
import openai
import pytest

from fanoos import cli
from fanoos.agent import Fanoos, build_system_prompt
from fanoos.cli import main
from fanoos.errors import AuthenticationFailedError, MissingAPIKeyError, RateLimitError, UnknownProviderError
from fanoos.providers import GEMINI, GROQ, PROVIDERS, XAI, get_provider, select_provider
from fanoos.sources import PortfolioSource
from fanoos.system_prompt import NO_LIVE_SEARCH_FOOTER, NO_LIVE_SEARCH_INSTRUCTIONS, SYSTEM_PROMPT

from .conftest import FakeClient, chat_chunks

SOURCE = PortfolioSource("url", "https://example.com", "Hello")
REQUEST = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")


def test_known_providers() -> None:
    assert list(PROVIDERS) == ["xai", "gemini", "groq"]
    assert XAI.live_search and not GEMINI.live_search and not GROQ.live_search
    assert GEMINI.free_tier and GROQ.free_tier


@pytest.mark.parametrize(
    ("keys", "expected"),
    [
        ({"XAI_API_KEY": "k", "GEMINI_API_KEY": "k"}, "xai"),
        ({"GEMINI_API_KEY": "k", "GROQ_API_KEY": "k"}, "gemini"),
        ({"GROQ_API_KEY": "k"}, "groq"),
    ],
)
def test_auto_selection_order(monkeypatch, keys: dict[str, str], expected: str) -> None:
    for name, value in keys.items():
        monkeypatch.setenv(name, value)
    assert select_provider().name == expected


def test_env_override(monkeypatch) -> None:
    monkeypatch.setenv("XAI_API_KEY", "k")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("FANOOS_PROVIDER", "groq")
    assert select_provider().name == "groq"


def test_explicit_provider_without_key(monkeypatch) -> None:
    monkeypatch.setenv("XAI_API_KEY", "k")
    with pytest.raises(MissingAPIKeyError, match="GEMINI_API_KEY") as exc:
        select_provider("gemini")
    assert "aistudio.google.com" in str(exc.value)
    assert "کلید" in str(exc.value)  # bilingual


def test_no_provider_configured() -> None:
    with pytest.raises(MissingAPIKeyError, match="No AI provider"):
        select_provider()


def test_unknown_provider() -> None:
    with pytest.raises(UnknownProviderError, match="xai, gemini, groq"):
        get_provider("openai")


def test_blank_key_counts_as_missing(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "   ")
    assert not GEMINI.configured


def test_system_prompt_is_verbatim_prefix() -> None:
    assert build_system_prompt(True).startswith(SYSTEM_PROMPT.strip())
    assert NO_LIVE_SEARCH_INSTRUCTIONS.strip() not in build_system_prompt(True)
    offline = build_system_prompt(False)
    assert offline.startswith(SYSTEM_PROMPT.strip())
    assert offline.rstrip().endswith(NO_LIVE_SEARCH_INSTRUCTIONS.strip())


def test_gemini_uses_chat_completions_without_tools(sample_reply: str) -> None:
    client = FakeClient(chat_chunks(sample_reply))
    agent = Fanoos(provider="gemini", client=client)
    assert agent.model == GEMINI.default_model and not agent.live_search
    review = agent.review(SOURCE)
    call = client.responses.calls[0]
    assert "tools" not in call and call["stream"] is True
    assert call["messages"][0]["content"].endswith(NO_LIVE_SEARCH_INSTRUCTIONS.strip() + "\n")
    assert review.provider == "gemini" and review.model == GEMINI.default_model
    assert review.live_search is False
    assert review.report.endswith(NO_LIVE_SEARCH_FOOTER)
    assert review.scores["visual_craft"] == 84


def test_footer_not_duplicated(sample_reply: str) -> None:
    reply = sample_reply.replace("\n```json", f"\n{NO_LIVE_SEARCH_FOOTER}\n```json", 1)
    review = Fanoos(provider="groq", client=FakeClient(chat_chunks(reply))).review(SOURCE)
    assert review.report.count(NO_LIVE_SEARCH_FOOTER) == 1


def test_xai_review_has_no_footer(sample_reply: str) -> None:
    from .conftest import text_events

    review = Fanoos(client=FakeClient(text_events(sample_reply))).review(SOURCE)
    assert review.live_search is True and NO_LIVE_SEARCH_FOOTER not in review.report
    assert review.to_dict()["provider"] == "xai"


def test_real_client_is_built_from_env(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    agent = Fanoos()
    assert agent.provider is GROQ
    assert str(agent._client.base_url).startswith("https://api.groq.com/openai/v1")
    assert agent._client.max_retries == 3
    assert "test-groq-key" not in repr(agent)


def test_gemini_bad_key_400_maps_to_auth_error() -> None:
    error = openai.BadRequestError(
        "API key not valid. Please pass a valid API key.", response=httpx.Response(400, request=REQUEST), body=None
    )
    with pytest.raises(AuthenticationFailedError, match="GEMINI_API_KEY"):
        list(Fanoos(provider="gemini", client=FakeClient(error=error)).stream(SOURCE))


def test_gemini_list_shaped_error_body_maps_to_auth_error() -> None:
    body = [{"error": {"code": 400, "message": "Please pass a valid API key", "status": "INVALID_ARGUMENT"}}]
    error = openai.BadRequestError("Error code: 400", response=httpx.Response(400, request=REQUEST), body=body)
    with pytest.raises(AuthenticationFailedError):
        list(Fanoos(provider="gemini", client=FakeClient(error=error)).stream(SOURCE))


def test_rate_limit_names_provider() -> None:
    error = openai.RateLimitError("slow down", response=httpx.Response(429, request=REQUEST), body=None)
    with pytest.raises(RateLimitError, match="Google Gemini rate limit") as exc:
        list(Fanoos(provider="gemini", client=FakeClient(error=error)).stream(SOURCE))
    assert "سهمیه" in str(exc.value)


def test_providers_command(monkeypatch, capsys) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    assert main(["providers"]) == 0
    out = capsys.readouterr().out
    assert "gemini" in out and "selected" in out and "configured" in out and "not set" in out
    assert "test-gemini-key" not in out


def test_review_provider_flag(monkeypatch, capsys, sample_reply: str) -> None:
    client = FakeClient(chat_chunks(sample_reply))
    monkeypatch.setattr(
        cli, "Fanoos", lambda provider=None, model=None: Fanoos(client=client, provider=provider, model=model)
    )
    monkeypatch.setattr(cli, "load_source", lambda target, fetch=True: PortfolioSource("url", target, ""))
    assert main(["review", "https://example.com", "--provider", "groq"]) == 0
    out = capsys.readouterr().out
    assert NO_LIVE_SEARCH_FOOTER in out and "groq" in out
