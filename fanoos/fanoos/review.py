"""The :class:`Review` data model and the parser for the model's output.

The model answers with a written review followed by a fenced ``json`` block
(see :data:`fanoos.system_prompt.OUTPUT_FORMAT_INSTRUCTIONS`). The parser reads
that block first. If it is missing or broken, it falls back to reading the
numbered Markdown sections the persona always writes, so a slightly
off-format reply still produces a usable review.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .errors import MalformedOutputError

SCORE_KEYS: tuple[str, ...] = (
    "narrative",
    "visual_craft",
    "case_study_depth",
    "english_quality",
    "international_readiness",
)
"""The five score criteria, in display order."""

SCORE_LABELS: dict[str, str] = {
    "narrative": "Narrative",
    "visual_craft": "Visual Craft",
    "case_study_depth": "Case Study Depth",
    "english_quality": "English Quality",
    "international_readiness": "International Readiness",
}
"""Human-readable label for each score key."""

_JSON_BLOCK = re.compile(r"```(?:json|JSON)?\s*\n(\{.*?\})\s*\n?```", re.DOTALL)
_PERSIAN = re.compile(r"[؀-ۿﭐ-﷿ﹰ-﻿]")


@dataclass(frozen=True)
class CriticalIssue:
    """A dealbreaker and the fix for it."""

    issue: str
    fix: str


@dataclass
class Review:
    """A structured portfolio review.

    Attributes:
        verdict: The one-line Persian verdict that opens every review.
        first_impression: The 10-second recruiter test.
        critical_issues: Dealbreakers, each paired with a fix.
        quick_wins: Fixes that take under an hour.
        next_actions: The next three prioritised actions.
        scores: 0-100 per criterion, keyed by :data:`SCORE_KEYS`.
        report: The written review as the model produced it (without the
            JSON block).
    """

    verdict: str
    first_impression: str
    critical_issues: list[CriticalIssue] = field(default_factory=list)
    quick_wins: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    scores: dict[str, int] = field(default_factory=dict)
    report: str = ""

    @property
    def overall_score(self) -> int | None:
        """Return the rounded mean of the available scores, or ``None`` if there are none."""
        if not self.scores:
            return None
        return round(sum(self.scores.values()) / len(self.scores))

    def to_dict(self, include_report: bool = False) -> dict[str, Any]:
        """Return the review as plain JSON-serialisable data.

        Args:
            include_report: Also include the full written report.

        Returns:
            A dictionary with the documented review fields.
        """
        data = asdict(self)
        if not include_report:
            data.pop("report")
        data["overall_score"] = self.overall_score
        return data


def contains_persian(text: str) -> bool:
    """Return ``True`` if ``text`` contains Persian/Arabic-script characters."""
    return bool(_PERSIAN.search(text))


def split_report(text: str) -> tuple[str, str | None]:
    """Separate the written review from the trailing JSON block.

    Args:
        text: The model's full reply.

    Returns:
        ``(report, json_text)``. ``json_text`` is ``None`` when no block is present.
    """
    matches = list(_JSON_BLOCK.finditer(text))
    if not matches:
        return text.strip(), None
    last = matches[-1]
    report = (text[: last.start()] + text[last.end() :]).strip()
    return report, last.group(1)


def parse_review(text: str) -> Review:
    """Parse the model's reply into a :class:`Review`.

    Args:
        text: The model's full reply.

    Returns:
        The parsed review.

    Raises:
        MalformedOutputError: If neither the JSON block nor the Markdown
            sections contain a usable review.
    """
    if not text or not text.strip():
        raise MalformedOutputError("The model returned an empty reply. Try again.")

    report, json_text = split_report(text)
    if json_text is not None:
        try:
            return _from_json(json.loads(json_text), report)
        except (ValueError, TypeError, AttributeError):
            pass  # fall through to the Markdown reader
    return _from_markdown(report)


# --- JSON ---------------------------------------------------------------------


def _clean_str(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _clean_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [s for s in (_clean_str(v) for v in value) if s]


def _clamp_score(value: Any) -> int:
    score = int(round(float(value)))
    return max(0, min(100, score))


def _normalise_key(key: str) -> str:
    return re.sub(r"[^a-z]+", "_", key.lower()).strip("_")


def _parse_scores(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    by_key = {_normalise_key(str(k)): v for k, v in raw.items()}
    scores: dict[str, int] = {}
    for key in SCORE_KEYS:
        if key in by_key:
            try:
                scores[key] = _clamp_score(by_key[key])
            except (TypeError, ValueError):
                continue
    return scores


def _from_json(data: dict[str, Any], report: str) -> Review:
    if not isinstance(data, dict):
        raise TypeError("JSON summary is not an object")
    issues: list[CriticalIssue] = []
    for item in data.get("critical_issues") or []:
        if isinstance(item, dict):
            issue = _clean_str(item.get("issue"))
            if issue:
                issues.append(CriticalIssue(issue=issue, fix=_clean_str(item.get("fix"))))
        elif _clean_str(item):
            issues.append(CriticalIssue(issue=_clean_str(item), fix=""))

    review = Review(
        verdict=_clean_str(data.get("verdict")),
        first_impression=_clean_str(data.get("first_impression")),
        critical_issues=issues,
        quick_wins=_clean_list(data.get("quick_wins")),
        next_actions=_clean_list(data.get("next_actions")),
        scores=_parse_scores(data.get("scores")),
        report=report,
    )
    if not review.verdict:
        review.verdict = _first_line(report)
    if not (review.verdict or review.first_impression or review.scores):
        raise ValueError("JSON summary is empty")
    return review


# --- Markdown fallback ----------------------------------------------------------

_SECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "first_impression": re.compile(r"first\s+impression|برداشت\s+اول|اولین\s+برداشت", re.I),
    "critical_issues": re.compile(r"critical\s+issues?|مشکلات\s+(حیاتی|اساسی|جدی)", re.I),
    "quick_wins": re.compile(r"quick\s+wins?|بردهای\s+سریع|اصلاحات\s+سریع", re.I),
    "next_actions": re.compile(r"next\s+(3|three)?\s*actions?|سه\s+اقدام|اقدامات\s+بعدی|گام\s+بعدی", re.I),
    "scores": re.compile(r"scores?|scoring|امتیاز", re.I),
}

_HEADING = re.compile(r"^\s{0,3}(?:#{1,6}\s*|\*\*|\d+[\).]\s*\**|[۱-۹][\).]\s*\**)(.+?)\**\s*:?\s*$")
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[\).]|[۰-۹]+[\).])\s+(.*\S)\s*$")
_SCORE_LINE = re.compile(r"([A-Za-z][A-Za-z ]+?)\s*[:：\-–—|]\s*\**\s*(\d{1,3})\s*(?:/\s*100)?")
_FIX_SPLIT = re.compile(r"\s*(?:→|->|—\s*fix:|fix:|راه\s*حل:|اصلاح:)\s*", re.I)


def _strip_md(line: str) -> str:
    return re.sub(r"[*_`]+", "", line).strip()


def _first_line(report: str) -> str:
    for line in report.splitlines():
        cleaned = _strip_md(line).lstrip("#").strip()
        if cleaned:
            return cleaned
    return ""


def _sections(report: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    current: str | None = None
    for line in report.splitlines():
        heading = _HEADING.match(line)
        if heading and len(heading.group(1)) < 80:
            title = _strip_md(heading.group(1))
            for name, pattern in _SECTION_PATTERNS.items():
                if pattern.search(title):
                    current = name
                    found.setdefault(name, [])
                    break
            else:
                if line.lstrip().startswith("#"):
                    current = None
                elif current:
                    found[current].append(line)
            continue
        if current:
            found[current].append(line)
    return found


def _bullets(lines: list[str]) -> list[str]:
    items = [_strip_md(m.group(1)) for m in (_BULLET.match(line) for line in lines) if m]
    return [i for i in items if i]


def _from_markdown(report: str) -> Review:
    sections = _sections(report)

    issues = []
    for item in _bullets(sections.get("critical_issues", [])):
        parts = _FIX_SPLIT.split(item, maxsplit=1)
        issues.append(CriticalIssue(issue=parts[0].strip(), fix=parts[1].strip() if len(parts) > 1 else ""))

    scores: dict[str, int] = {}
    for line in sections.get("scores", []) or report.splitlines():
        for label, value in _SCORE_LINE.findall(_strip_md(line)):
            key = _normalise_key(label)
            if key in SCORE_KEYS:
                scores[key] = _clamp_score(value)

    first_impression = " ".join(_strip_md(line) for line in sections.get("first_impression", []) if _strip_md(line))

    review = Review(
        verdict=_first_line(report),
        first_impression=first_impression,
        critical_issues=issues,
        quick_wins=_bullets(sections.get("quick_wins", [])),
        next_actions=_bullets(sections.get("next_actions", []))[:3],
        scores=scores,
        report=report,
    )
    if not (review.first_impression or review.critical_issues or review.scores):
        raise MalformedOutputError(
            "Could not read a structured review from the model's reply "
            "(no JSON summary and no recognisable sections). Try again, or use "
            "--raw to see the reply as-is."
        )
    return review


__all__ = [
    "SCORE_KEYS",
    "SCORE_LABELS",
    "CriticalIssue",
    "Review",
    "contains_persian",
    "split_report",
    "parse_review",
]
