"""LLM client factory — selects provider from settings."""

from __future__ import annotations

from functools import lru_cache

from urie.config import get_settings
from urie.llm.base import LLMClient
from urie.llm.providers.mock_client import MockLLMClient


DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
    "mock": "mock-v1",
}


def build_llm_client(
    provider: str | None = None,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> LLMClient:
    """
    Construct an LLM client. Defaults to mock when provider=mock or no API key
    for a real provider — so local/dev never breaks.
    """
    settings = get_settings()
    prov = (provider or settings.llm_provider or "mock").lower().strip()
    key = api_key if api_key is not None else settings.llm_api_key
    url = base_url if base_url is not None else settings.llm_base_url
    mdl = model if model else (settings.llm_model or DEFAULT_MODELS.get(prov, ""))

    if prov == "mock" or (prov in ("openai", "anthropic") and not key):
        return MockLLMClient()

    if prov == "openai":
        from urie.llm.providers.openai_client import OpenAICompatibleClient

        return OpenAICompatibleClient(
            key,
            base_url=url or "https://api.openai.com/v1",
            model=mdl or DEFAULT_MODELS["openai"],
            timeout_s=settings.llm_timeout_s,
            max_retries=settings.llm_max_retries,
            default_temperature=settings.llm_temperature,
        )

    if prov == "anthropic":
        from urie.llm.providers.anthropic_client import AnthropicClient

        return AnthropicClient(
            key,
            base_url=url or "https://api.anthropic.com",
            model=mdl or DEFAULT_MODELS["anthropic"],
            timeout_s=settings.llm_timeout_s,
            max_retries=settings.llm_max_retries,
            default_temperature=settings.llm_temperature,
        )

    # Unknown provider → safe mock
    return MockLLMClient()


@lru_cache
def get_llm_client() -> LLMClient:
    return build_llm_client()
