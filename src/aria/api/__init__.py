"""API layer for LLM provider integrations."""

from aria.api.base import LLMClient
from aria.api.gemini import GeminiClient
from aria.api.openrouter import OpenRouterClient

__all__ = ["LLMClient", "GeminiClient", "OpenRouterClient", "create_llm_client"]


def create_llm_client(
    provider: str,
    model_name: str,
    gemini_api_key: str | None = None,
    openrouter_api_key: str | None = None,
) -> LLMClient:
    """Factory that returns the correct LLMClient for the given provider.

    Args:
        provider: Provider identifier — ``"gemini"`` or ``"openrouter"``.
        model_name: Model name appropriate for the selected provider.
        gemini_api_key: Google Gemini API key (required when provider is ``"gemini"``).
        openrouter_api_key: OpenRouter API key (required when provider is ``"openrouter"``).

    Returns:
        A fully-configured :class:`LLMClient` instance.

    Raises:
        aria.exceptions.APIError: When the API key for the chosen provider is missing.
        ValueError: When an unrecognised provider string is given.
    """
    if provider == "gemini":
        return GeminiClient(api_key=gemini_api_key or "", model_name=model_name)
    if provider == "openrouter":
        return OpenRouterClient(api_key=openrouter_api_key or "", model_name=model_name)
    raise ValueError(
        f"Unknown LLM provider '{provider}'. "
        "Expected 'gemini' or 'openrouter'."
    )
