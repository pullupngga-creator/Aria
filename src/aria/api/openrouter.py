"""OpenRouter LLM client implementation (OpenAI-compatible API)."""

import asyncio
import logging
from collections.abc import AsyncIterator

import aiohttp
from openai import AsyncOpenAI
from openai import APIConnectionError, APIStatusError, APITimeoutError

from aria.api.base import LLMClient
from aria.exceptions import APIError

logger = logging.getLogger(__name__)

# OpenRouter base URL (OpenAI-compatible)
_OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
_OPENROUTER_KEY_VALIDATION_URL: str = "https://openrouter.ai/api/v1/auth/key"

# Retry configuration (matches GeminiClient)
_MAX_RETRIES: int = 3
_BACKOFF_SECONDS: list[float] = [1.0, 2.0, 4.0]
_DEFAULT_TIMEOUT: float = 30.0


class OpenRouterClient(LLMClient):
    """OpenRouter LLM client using the OpenAI-compatible API.

    OpenRouter routes requests to many providers (Meta, Anthropic, OpenAI, etc.)
    through a single OpenAI-compatible endpoint.

    Supports streaming and non-streaming chat completions with retry logic.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "meta-llama/llama-3-70b-instruct",
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the OpenRouter client.

        Args:
            api_key: OpenRouter API key (https://openrouter.ai/keys).
            model_name: OpenRouter model identifier (e.g., 'meta-llama/llama-3-70b-instruct').
            timeout: Maximum seconds to wait for a response.
        """
        if not api_key:
            raise APIError(
                "OpenRouter API key is not configured. "
                "Set the OPENROUTER_API_KEY environment variable or add it in settings."
            )
        self._api_key = api_key
        self._model_name = model_name
        self._timeout = timeout
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=_OPENROUTER_BASE_URL,
            timeout=self._timeout,
            max_retries=0,  # We handle retries manually
        )

    def _build_messages(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None,
    ) -> list[dict[str, str]]:
        """Build the OpenAI-format messages list.

        Prepends the system prompt (if any) as a system role message,
        then maps all user/assistant messages directly (roles are identical).

        Args:
            messages: Aria internal message list (role: user|assistant, content: str).
            system_prompt: Optional system instruction.

        Returns:
            OpenAI-compatible message list ready for the API.
        """
        result: list[dict[str, str]] = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        for msg in messages:
            role = msg.get("role", "")
            if role in ("user", "assistant"):
                result.append({"role": role, "content": msg["content"]})
        return result

    async def send_message(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> str:
        """Send conversation to OpenRouter and return the response text.

        Args:
            messages: Conversation history; last item must be the new user message.
            system_prompt: Optional system instruction prepended as a system role message.

        Returns:
            The assistant's response text.

        Raises:
            APIError: On authentication failure, timeout, or persistent service errors.
        """
        if not messages:
            raise APIError("Cannot send an empty message list.")

        api_messages = self._build_messages(messages, system_prompt)

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model_name,
                    messages=api_messages,  # type: ignore[arg-type]
                    stream=False,
                )
                text = response.choices[0].message.content or "No response generated."
                logger.info(
                    "OpenRouter response received",
                    extra={
                        "response_length": len(text),
                        "model": self._model_name,
                        "attempt": attempt + 1,
                    },
                )
                return text

            except APIStatusError as e:
                if e.status_code == 401:
                    logger.error("OpenRouter API key is invalid (401)")
                    raise APIError(
                        "Invalid OpenRouter API key. Please check your settings."
                    ) from e
                if e.status_code == 429:
                    last_error = e
                    wait = _BACKOFF_SECONDS[attempt]
                    logger.warning(
                        "OpenRouter rate limit (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1, _MAX_RETRIES, wait, str(e),
                    )
                    await asyncio.sleep(wait)
                elif e.status_code >= 500:
                    last_error = e
                    wait = _BACKOFF_SECONDS[attempt]
                    logger.warning(
                        "OpenRouter server error (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1, _MAX_RETRIES, wait, str(e),
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("OpenRouter client error: %s", e)
                    raise APIError(f"OpenRouter API error: {e}") from e

            except APITimeoutError as e:
                logger.error("OpenRouter request timed out after %.1fs", self._timeout)
                raise APIError(
                    f"Request timed out after {int(self._timeout)}s. Please try again."
                ) from e

            except APIConnectionError as e:
                last_error = e
                wait = _BACKOFF_SECONDS[attempt]
                logger.warning(
                    "OpenRouter connection error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1, _MAX_RETRIES, wait, str(e),
                )
                await asyncio.sleep(wait)

        logger.error("OpenRouter retries exhausted after %d attempts", _MAX_RETRIES)
        raise APIError(
            "OpenRouter service is temporarily unavailable. Please try again later."
        ) from last_error

    async def send_message_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Send conversation to OpenRouter and stream the response chunk-by-chunk.

        Args:
            messages: Conversation history; last item must be the new user message.
            system_prompt: Optional system instruction.

        Yields:
            Response text chunks as they become available.

        Raises:
            APIError: On authentication failure, timeout, or persistent service errors.
        """
        if not messages:
            raise APIError("Cannot send an empty message list.")

        api_messages = self._build_messages(messages, system_prompt)

        last_error: Exception | None = None
        stream = None
        for attempt in range(_MAX_RETRIES):
            try:
                stream = await self._client.chat.completions.create(
                    model=self._model_name,
                    messages=api_messages,  # type: ignore[arg-type]
                    stream=True,
                )
                break

            except APIStatusError as e:
                if e.status_code == 401:
                    logger.error("OpenRouter API key is invalid (401)")
                    raise APIError(
                        "Invalid OpenRouter API key. Please check your settings."
                    ) from e
                if e.status_code == 429:
                    last_error = e
                    wait = _BACKOFF_SECONDS[attempt]
                    logger.warning(
                        "OpenRouter rate limit (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1, _MAX_RETRIES, wait, str(e),
                    )
                    await asyncio.sleep(wait)
                elif e.status_code >= 500:
                    last_error = e
                    wait = _BACKOFF_SECONDS[attempt]
                    logger.warning(
                        "OpenRouter server error (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1, _MAX_RETRIES, wait, str(e),
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("OpenRouter client error: %s", e)
                    raise APIError(f"OpenRouter API error: {e}") from e

            except APITimeoutError as e:
                logger.error("OpenRouter stream request timed out after %.1fs", self._timeout)
                raise APIError(
                    f"Request timed out after {int(self._timeout)}s. Please try again."
                ) from e

            except APIConnectionError as e:
                last_error = e
                wait = _BACKOFF_SECONDS[attempt]
                logger.warning(
                    "OpenRouter connection error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1, _MAX_RETRIES, wait, str(e),
                )
                await asyncio.sleep(wait)

        if stream is None:
            logger.error("OpenRouter retries exhausted after %d attempts", _MAX_RETRIES)
            raise APIError(
                "OpenRouter service is temporarily unavailable. Please try again later."
            ) from last_error

        try:
            async for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                yield delta
        except APIStatusError as e:
            logger.error("OpenRouter stream error during generation: %s", e)
            raise APIError(f"OpenRouter API stream error: {e}") from e
        except Exception as e:
            logger.error("Unexpected error during OpenRouter streaming: %s", e)
            raise APIError(f"OpenRouter streaming error: {e}") from e

    async def validate_key(self) -> bool:
        """Validate the OpenRouter API key using the auth metadata endpoint.

        Uses a lightweight GET to https://openrouter.ai/api/v1/auth/key
        which returns key status without consuming credits.

        Returns:
            True if the key is valid.

        Raises:
            APIError: If the key is invalid or the request fails.
        """
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    _OPENROUTER_KEY_VALIDATION_URL,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(
                            "OpenRouter API key validated (label=%s)",
                            data.get("data", {}).get("label", "unknown"),
                        )
                        return True
                    if resp.status == 401:
                        logger.warning("OpenRouter API key validation failed: 401 Unauthorized")
                        raise APIError("Invalid OpenRouter API key. Please check your settings.")
                    body = await resp.text()
                    logger.error(
                        "OpenRouter key validation unexpected status %d: %s", resp.status, body
                    )
                    raise APIError(
                        f"OpenRouter key validation failed (HTTP {resp.status})."
                    )
        except APIError:
            raise
        except aiohttp.ClientError as e:
            logger.error("OpenRouter key validation network error: %s", e)
            raise APIError(f"Failed to reach OpenRouter: {e}") from e
        except Exception as e:
            logger.error("Unexpected error during OpenRouter key validation", exc_info=True)
            raise APIError(f"Unexpected error validating OpenRouter API key: {e}") from e
