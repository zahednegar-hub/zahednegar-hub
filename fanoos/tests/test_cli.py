"""Tests for fanoos.cli. The agent is replaced by one using a fake client."""

from __future__ import annotations

import json

import pytest

from fanoos import cli
from fanoos.agent import Fanoos
from fanoos.cli import ReportStream, load_dotenv, main
from fanoos.sources import PortfolioSource

from .conftest import FakeClient, text_events


@pytest.fixture
def fake_agent(monkeypatch, sample_reply: str) -> FakeClient:
    client = FakeClient(text_events(sample_reply))
    monkeypatch.setattr(cli, "Fanoos", lambda model=None: Fanoos(client=client, model=model))
    monkeypatch.setattr(cli, "load_source", lambda target, fetch=True: PortfolioSource("url", target, "page text"))
    return client


def test_help(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "review" in capsys.readouterr().out


def test_no_command_prints_help(capsys) -> None:
    assert main([]) == 0
    assert "usage" in capsys.readouterr().out


def test_review_json(fake_agent, capsys) -> None:
    assert main(["review", "https://example.com", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["scores"]["visual_craft"] == 84
    assert data["verdict"].startswith("پورتفولیوی")


def test_review_streams_report_and_scorecard(fake_agent, capsys) -> None:
    assert main(["review", "https://example.com", "--lang", "en", "--model", "m"]) == 0
    out = capsys.readouterr().out
    assert "First Impression" in out
    assert "```json" not in out and '"scores"' not in out
    assert "Overall" in out and "67/100" in out
    assert fake_agent.responses.calls[0]["model"] == "m"


def test_review_no_stream(fake_agent, capsys) -> None:
    assert main(["review", "https://example.com", "--no-stream"]) == 0
    assert "Visual Craft" in capsys.readouterr().out


def test_review_raw(fake_agent, capsys) -> None:
    assert main(["review", "https://example.com", "--raw"]) == 0
    assert "```json" in capsys.readouterr().out


def test_missing_key_message(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "load_source", lambda target, fetch=True: PortfolioSource("url", target, ""))
    assert main(["review", "https://example.com"]) == 2
    err = capsys.readouterr().err
    assert "XAI_API_KEY is not set" in err


def test_bad_path_message(monkeypatch, capsys) -> None:
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    assert main(["review", "missing.pdf"]) == 7
    assert "No such file" in capsys.readouterr().err


def test_malformed_output_exit_code(monkeypatch, capsys) -> None:
    client = FakeClient(text_events("no structure here"))
    monkeypatch.setattr(cli, "Fanoos", lambda model=None: Fanoos(client=client))
    monkeypatch.setattr(cli, "load_source", lambda target, fetch=True: PortfolioSource("url", target, ""))
    assert main(["review", "https://example.com", "--json"]) == 6
    assert "--raw" in capsys.readouterr().err


@pytest.mark.parametrize("size", [1, 3, 8, 50])
def test_report_stream_hides_json(size: int, sample_reply: str) -> None:
    stream = ReportStream()
    shown = "".join(stream.feed(sample_reply[i : i + size]) for i in range(0, len(sample_reply), size)) + stream.flush()
    assert shown.rstrip() == sample_reply.split("```json")[0].rstrip()


def test_report_stream_keeps_other_code_fences() -> None:
    stream = ReportStream()
    text = "Use `rem` units and ```css\na{}\n``` blocks."
    assert stream.feed(text) + stream.flush() == text


def test_load_dotenv_does_not_override(tmp_path, monkeypatch) -> None:
    env = tmp_path / ".env"
    env.write_text("# comment\nXAI_API_KEY='test-key-from-file'\nFANOOS_MODEL=env-model\n", encoding="utf-8")
    monkeypatch.setenv("FANOOS_MODEL", "real-model")
    load_dotenv(env)
    import os

    assert os.environ["XAI_API_KEY"] == "test-key-from-file"
    assert os.environ["FANOOS_MODEL"] == "real-model"
