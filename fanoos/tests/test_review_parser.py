"""Tests for fanoos.review."""

from __future__ import annotations

import pytest

from fanoos.errors import MalformedOutputError
from fanoos.review import SCORE_KEYS, CriticalIssue, contains_persian, parse_review, split_report


def test_parses_json_block(sample_reply: str) -> None:
    review = parse_review(sample_reply)
    assert review.verdict.startswith("پورتفولیوی قوی")
    assert review.critical_issues[0] == CriticalIssue(
        issue="No measurable impact in case studies", fix="Add one outcome metric per project."
    )
    assert review.quick_wins == ["Add alt text to hero images", "Shorten the About headline"]
    assert len(review.next_actions) == 3
    assert set(review.scores) == set(SCORE_KEYS)
    assert review.scores["visual_craft"] == 84
    assert review.overall_score == round((62 + 84 + 55 + 70 + 66) / 5)


def test_report_excludes_json_block(sample_reply: str) -> None:
    review = parse_review(sample_reply)
    assert "```" not in review.report
    assert "First Impression" in review.report


def test_markdown_fallback_when_json_missing(sample_prose: str) -> None:
    review = parse_review(sample_prose)
    assert "پورتفولیوی قوی" in review.verdict
    assert review.first_impression.startswith("Clean visual hierarchy")
    assert review.critical_issues[1].fix == "Flip directional icons under dir=rtl."
    assert review.quick_wins[0] == "Add alt text to hero images"
    assert review.next_actions == ["Rewrite Venture Compass case study", "Fix RTL icons", "Polish English bio"]
    assert review.scores == {
        "narrative": 62,
        "visual_craft": 84,
        "case_study_depth": 55,
        "english_quality": 70,
        "international_readiness": 66,
    }


def test_markdown_fallback_when_json_broken(sample_prose: str) -> None:
    review = parse_review(sample_prose + "\n```json\n{not valid json\n```")
    assert review.scores["narrative"] == 62


def test_scores_are_clamped_and_keys_normalised() -> None:
    reply = '```json\n{"verdict": "v", "scores": {"Visual Craft": 140, "narrative": -5, "bogus": 9}}\n```'
    review = parse_review(reply)
    assert review.scores == {"visual_craft": 100, "narrative": 0}


def test_string_items_and_missing_fields_are_tolerated() -> None:
    reply = (
        '```json\n{"verdict": "v", "first_impression": "ok", "critical_issues": ["bad nav"], "quick_wins": "one"}\n```'
    )
    review = parse_review(reply)
    assert review.critical_issues == [CriticalIssue(issue="bad nav", fix="")]
    assert review.quick_wins == ["one"]
    assert review.next_actions == []
    assert review.overall_score is None


def test_uses_last_json_block() -> None:
    reply = (
        'Example:\n```json\n{"verdict": "old"}\n```\nFinal:\n```json\n{"verdict": "new", "first_impression": "x"}\n```'
    )
    assert parse_review(reply).verdict == "new"


@pytest.mark.parametrize("reply", ["", "   ", "Just some text with no structure at all."])
def test_malformed_output_raises(reply: str) -> None:
    with pytest.raises(MalformedOutputError):
        parse_review(reply)


def test_to_dict_is_json_friendly(sample_reply: str) -> None:
    data = parse_review(sample_reply).to_dict()
    assert "report" not in data
    assert data["critical_issues"][0]["fix"]
    assert data["overall_score"] == 67
    assert "report" in parse_review(sample_reply).to_dict(include_report=True)


def test_split_report_without_block() -> None:
    assert split_report("hello") == ("hello", None)


def test_contains_persian() -> None:
    assert contains_persian("فانوس")
    assert not contains_persian("lantern")
