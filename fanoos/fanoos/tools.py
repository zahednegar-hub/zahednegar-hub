"""xAI Agent Tools configuration.

Fanoos uses xAI's *server-side* Agent Tools: the model decides when to search,
xAI runs the search and feeds the results back to the model, all inside a
single Responses API call. The client never has to execute a tool itself.
"""

from __future__ import annotations

from typing import Any

WEB_SEARCH: dict[str, Any] = {"type": "web_search"}
"""Real-time web search and page browsing (current design and portfolio trends)."""

X_SEARCH: dict[str, Any] = {"type": "x_search"}
"""Search posts on X (what designers and recruiters are discussing right now)."""


def review_tools() -> list[dict[str, Any]]:
    """Return the tools enabled on every review request.

    A fresh list is returned each time so callers can modify it safely.

    Returns:
        The ``tools`` payload for ``client.responses.create``.
    """
    return [dict(WEB_SEARCH), dict(X_SEARCH)]


__all__ = ["WEB_SEARCH", "X_SEARCH", "review_tools"]
