"""AI providers Fanoos can run on.

Every provider is reached through an OpenAI-compatible endpoint, so one client
library covers all of them. Only xAI offers server-side live search
(``web_search`` / ``x_search``); on the others Fanoos answers from the model's
own knowledge and marks the report «بدون جستجوی زنده».

Selection order: ``--provider`` / ``FANOOS_PROVIDER`` if set, otherwise the
first provider whose API key is present, in the order xai → gemini → groq.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from .errors import MissingAPIKeyError, UnknownProviderError

PROVIDER_ENV: str = "FANOOS_PROVIDER"
MODEL_ENV: str = "FANOOS_MODEL"


@dataclass(frozen=True)
class Provider:
    """An OpenAI-compatible AI provider.

    Attributes:
        name: Short identifier used in ``FANOOS_PROVIDER`` (``xai``, ``gemini``, ``groq``).
        label: Display name.
        base_url: OpenAI-compatible API root.
        env_var: Environment variable holding the API key.
        default_model: Model used when ``FANOOS_MODEL`` / ``--model`` is not given.
        live_search: Whether the provider runs ``web_search`` and ``x_search`` server-side.
        free_tier: Whether the provider offers a free tier.
        signup_url: Where to create an API key.
    """

    name: str
    label: str
    base_url: str
    env_var: str
    default_model: str
    live_search: bool
    free_tier: bool
    signup_url: str

    def api_key(self) -> str | None:
        """Return the API key from the environment, or ``None`` if unset. Never log the result."""
        value = os.environ.get(self.env_var, "").strip()
        return value or None

    @property
    def configured(self) -> bool:
        """Whether this provider's API key is present in the environment."""
        return self.api_key() is not None


XAI = Provider(
    name="xai",
    label="xAI Grok",
    base_url="https://api.x.ai/v1",
    env_var="XAI_API_KEY",
    default_model="grok-4-1-fast-reasoning",
    live_search=True,
    free_tier=False,
    signup_url="https://console.x.ai",
)

GEMINI = Provider(
    name="gemini",
    label="Google Gemini",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    env_var="GEMINI_API_KEY",
    # Google's alias for the current Flash model; pinned IDs such as gemini-2.0-flash get retired.
    default_model="gemini-flash-latest",
    live_search=False,
    free_tier=True,
    signup_url="https://aistudio.google.com/apikey",
)

GROQ = Provider(
    name="groq",
    label="Groq",
    base_url="https://api.groq.com/openai/v1",
    env_var="GROQ_API_KEY",
    # Groq's recommended replacement for the retired llama-3.3-70b-versatile.
    default_model="openai/gpt-oss-120b",
    live_search=False,
    free_tier=True,
    signup_url="https://console.groq.com/keys",
)

PROVIDERS: dict[str, Provider] = {p.name: p for p in (XAI, GEMINI, GROQ)}
"""All known providers, in auto-selection order."""


def get_provider(name: str) -> Provider:
    """Look up a provider by name (case-insensitive).

    Raises:
        UnknownProviderError: If ``name`` is not a known provider.
    """
    key = name.strip().lower()
    if key not in PROVIDERS:
        raise UnknownProviderError(name, list(PROVIDERS))
    return PROVIDERS[key]


def select_provider(name: str | None = None) -> Provider:
    """Choose the provider to use.

    Args:
        name: Explicit choice (for example from ``--provider``). Falls back to
            ``FANOOS_PROVIDER``, then to the first configured provider.

    Returns:
        The selected provider. Its key is guaranteed to be set.

    Raises:
        UnknownProviderError: If the explicit choice is not a known provider.
        MissingAPIKeyError: If the chosen provider has no key, or none is configured.
    """
    choice = name or os.environ.get(PROVIDER_ENV, "").strip()
    if choice:
        provider = get_provider(choice)
        if not provider.configured:
            raise MissingAPIKeyError(provider.env_var, provider.signup_url)
        return provider
    for provider in PROVIDERS.values():
        if provider.configured:
            return provider
    raise MissingAPIKeyError()


def preferred_provider_name() -> str | None:
    """Return the provider :func:`select_provider` would pick, or ``None`` if it would fail."""
    try:
        return select_provider().name
    except (MissingAPIKeyError, UnknownProviderError):
        return None


__all__ = [
    "Provider",
    "PROVIDERS",
    "XAI",
    "GEMINI",
    "GROQ",
    "PROVIDER_ENV",
    "MODEL_ENV",
    "get_provider",
    "select_provider",
    "preferred_provider_name",
]
