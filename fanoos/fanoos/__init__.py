"""Fanoos (فانوس): a bilingual AI portfolio critic and career coach for designers.

Quick use::

    from fanoos import Fanoos, load_source

    review = Fanoos().review(load_source("https://example.com"), language="en")
    print(review.verdict, review.overall_score)
"""

from __future__ import annotations

__version__ = "0.1.0"

from .agent import DEFAULT_MODEL, Fanoos
from .errors import (
    APIError,
    AuthenticationFailedError,
    FanoosError,
    MalformedOutputError,
    MissingAPIKeyError,
    NetworkError,
    RateLimitError,
    SourceError,
)
from .review import SCORE_KEYS, CriticalIssue, Review, parse_review
from .sources import PortfolioSource, load_source
from .system_prompt import SYSTEM_PROMPT

__all__ = [
    "__version__",
    "Fanoos",
    "DEFAULT_MODEL",
    "Review",
    "CriticalIssue",
    "SCORE_KEYS",
    "parse_review",
    "PortfolioSource",
    "load_source",
    "SYSTEM_PROMPT",
    "FanoosError",
    "MissingAPIKeyError",
    "AuthenticationFailedError",
    "NetworkError",
    "RateLimitError",
    "APIError",
    "MalformedOutputError",
    "SourceError",
]
