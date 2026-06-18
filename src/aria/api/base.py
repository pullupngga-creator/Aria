"""Abstract base class for LLM provider clients."""

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Abstract interface for all LLM provider integrations.

    All providers (Gemini, Claude, OpenAI) must implement this contract
    to ensure a unified interface for the chat orchestration layer.
    """

    @abstractmethod
    async def send_message(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> str:
        """Send conversation history and return the assistant's response text.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                      Roles: 'user', 'assistant', 'system'.
            system_prompt: Optional system instruction prepended to the conversation.

        Returns:
            The assistant's response as plain text.

        Raises:
            aria.exceptions.APIError: On any provider-side failure.
        """
        ...

    @abstractmethod
    async def validate_key(self) -> bool:
        """Check whether the configured API key is valid.

        Returns:
            True if the key is valid, False otherwise.

        Raises:
            aria.exceptions.APIError: On unexpected errors during validation.
        """
        ...
