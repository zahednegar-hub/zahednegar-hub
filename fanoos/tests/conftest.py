"""Shared test fixtures. No test touches the network."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

SAMPLE_JSON = {
    "verdict": "پورتفولیوی قوی با روایت ضعیف؛ کیس‌استادی‌ها نتیجه‌ی قابل‌اندازه‌گیری ندارند.",
    "first_impression": "Clean visual hierarchy, but the value proposition is unclear in the first 10 seconds.",
    "critical_issues": [
        {"issue": "No measurable impact in case studies", "fix": "Add one outcome metric per project."},
        {"issue": "Persian pages mirror icons incorrectly", "fix": "Flip directional icons under dir=rtl."},
    ],
    "quick_wins": ["Add alt text to hero images", "Shorten the About headline"],
    "next_actions": ["Rewrite Venture Compass case study", "Fix RTL icons", "Polish English bio"],
    "scores": {
        "narrative": 62,
        "visual_craft": 84,
        "case_study_depth": 55,
        "english_quality": 70,
        "international_readiness": 66,
    },
}

SAMPLE_PROSE = """\
**پورتفولیوی قوی با روایت ضعیف؛ کیس‌استادی‌ها نتیجه‌ی قابل‌اندازه‌گیری ندارند.**

## 1) First Impression
Clean visual hierarchy, but the value proposition is unclear in the first 10 seconds.

## 2) Critical Issues
- No measurable impact in case studies → Add one outcome metric per project.
- Persian pages mirror icons incorrectly → Flip directional icons under dir=rtl.

## 3) Quick Wins
- Add alt text to hero images
- Shorten the About headline

## 4) Next 3 Actions
1. Rewrite Venture Compass case study
2. Fix RTL icons
3. Polish English bio

## Scores
- Narrative: 62/100
- Visual Craft: 84/100
- Case Study Depth: 55/100
- English Quality: 70/100
- International Readiness: 66/100
"""

SAMPLE_REPLY = SAMPLE_PROSE + "\n```json\n" + json.dumps(SAMPLE_JSON, ensure_ascii=False, indent=2) + "\n```\n"


def text_events(text: str, size: int = 7) -> list[SimpleNamespace]:
    """Split ``text`` into fake Responses API streaming events."""
    events = [SimpleNamespace(type="response.created")]
    events += [
        SimpleNamespace(type="response.output_text.delta", delta=text[i : i + size]) for i in range(0, len(text), size)
    ]
    events.append(SimpleNamespace(type="response.completed"))
    return events


class FakeResponses:
    def __init__(self, events=None, error: BaseException | None = None) -> None:
        self.events = events or []
        self.error = error
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return iter(self.events)


class FakeClient:
    def __init__(self, events=None, error: BaseException | None = None) -> None:
        self.responses = FakeResponses(events, error)


@pytest.fixture
def sample_reply() -> str:
    return SAMPLE_REPLY


@pytest.fixture
def sample_prose() -> str:
    return SAMPLE_PROSE


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    """Keep the real key and any local .env out of every test."""
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("FANOOS_MODEL", raising=False)
    monkeypatch.chdir(tmp_path)
