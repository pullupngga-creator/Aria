"""Google Gemini LLM client implementation."""

import asyncio
import logging

from google import genai
from google.genai import types
from google.genai.errors import APIError as GenaiAPIError
from google.genai.errors import ClientError, ServerError

from aria.api.base import LLMClient
from aria.exceptions import APIError

logger = logging.getLogger(__name__)

# Retry configuration
_MAX_RETRIES: int = 3
_BACKOFF_SECONDS: list[float] = [1.0, 2.0, 4.0]
_DEFAULT_TIMEOUT: float = 30.0

# Role mapping: Aria internal role -> Gemini role
_ROLE_MAP: dict[str, str] = {
    "user": "user",
    "assistant": "model",
}


class GeminiClient(LLMClient):
    """Google Gemini LLM client wrapping google-genai.

    Supports non-streaming chat completions with retry logic and timeout.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-1.5-pro",
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize Gemini client.

        Args:
            api_key: Google AI Studio / Gemini API key.
            model_name: Gemini model identifier (e.g., 'gemini-1.5-pro').
            timeout: Maximum seconds to wait for a response.
        """
        if not api_key:
            raise APIError(
                "Gemini API key is not configured. "
                "Set the GEMINI_API_KEY environment variable."
            )
        self._api_key = api_key
        self._model_name = model_name
        self._timeout = timeout
        self._client = genai.Client(api_key=self._api_key)

    def _build_contents(self, messages: list[dict[str, str]]) -> list[types.Content]:
        """Convert Aria message list to Gemini Content objects.

        Only includes user and assistant messages.
        Excludes the last user message which is sent as the new turn.
        """
        contents: list[types.Content] = []
        # Exclude the last message (the new user turn) from history
        for msg in messages[:-1]:
            role = _ROLE_MAP.get(msg.get("role", ""))
            if role is not None:
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg["content"])],
                    )
                )
        return contents

    async def send_message(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> str:
        """Send conversation to Gemini and return the response text.

        Args:
            messages: Conversation history; last item must be the new user message.
            system_prompt: Optional system instruction (passed via generation_config).

        Returns:
            The assistant's response text.

        Raises:
            APIError: On authentication failure, timeout, or persistent service errors.
        """
        if not messages:
            raise APIError("Cannot send an empty message list.")

        # Build contents: history + current user turn
        history_contents = self._build_contents(messages)
        current_turn = types.Content(
            role="user",
            parts=[types.Part.from_text(text=messages[-1]["content"])],
        )
        all_contents = [*history_contents, current_turn]

        # Build config with optional system instruction
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
        ) if system_prompt else None

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=self._model_name,
                        contents=all_contents,
                        config=config,
                    ),
                    timeout=self._timeout,
                )
                text = response.text or "No response generated"
                logger.info(
                    "Gemini response received",
                    extra={"response_length": len(text), "attempt": attempt + 1},
                )
                return text

            except ClientError as e:
                if e.code == 401:
                    logger.error("Gemini API key is invalid")
                    raise APIError(
                        "Invalid Gemini API key. Please check your GEMINI_API_KEY."
                    ) from e
                if e.code == 429:
                    last_error = e
                    wait = _BACKOFF_SECONDS[attempt]
                    logger.warning(
                        "Gemini API rate limit (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1, _MAX_RETRIES, wait, str(e),
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("Unexpected Gemini client error: %s", e)
                    raise APIError(f"Gemini API error: {e}") from e

            except ServerError as e:
                last_error = e
                wait = _BACKOFF_SECONDS[attempt]
                logger.warning(
                    "Gemini API error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1, _MAX_RETRIES, wait, str(e),
                )
                await asyncio.sleep(wait)

            except TimeoutError as e:
                logger.error("Gemini API request timed out after %.1fs", self._timeout)
                raise APIError(
                    f"Request timed out after {int(self._timeout)}s. Please try again."
                ) from e

            except GenaiAPIError as e:
                logger.error("Unexpected Gemini API error: %s", e)
                raise APIError(f"Gemini API error: {e}") from e

        # All retries exhausted
        logger.error("Gemini API retries exhausted after %d attempts", _MAX_RETRIES)
        raise APIError(
            "Gemini service is temporarily unavailable. Please try again later."
        ) from last_error

    async def validate_key(self) -> bool:
        """Check if the configured API key is valid by listing available models.

        Returns:
            True if the key is valid.

        Raises:
            APIError: On unexpected errors during validation.
        """
        try:
            pager = await self._client.aio.models.list()
            count = 0
            async for _ in pager:
                count += 1
            logger.info("API key validated successfully (%d models available)", count)
            return True
        except ClientError as e:
            if e.code == 401:
                logger.warning("API key validation failed: unauthenticated")
                raise APIError("Invalid Gemini API key.") from e
            logger.error("API key validation failed: %s", e)
            raise APIError(f"Failed to validate API key: {e}") from e
        except GenaiAPIError as e:
            logger.error("API key validation failed: %s", e)
            raise APIError(f"Failed to validate API key: {e}") from e
        except Exception as e:
            logger.error("Unexpected error during key validation", exc_info=True)
            raise APIError(f"Unexpected error validating API key: {e}") from e
