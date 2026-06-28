"""Unit tests for the OpenRouterClient and create_llm_client factory."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError

from aria.api import create_llm_client
from aria.api.openrouter import OpenRouterClient
from aria.exceptions import APIError


# ── Fake helpers ─────────────────────────────────────────────────────────────


def _make_chat_completion(content: str) -> MagicMock:
    """Build a fake non-streaming ChatCompletion response."""
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_stream_chunk(content: str | None) -> MagicMock:
    """Build a fake streaming chunk."""
    delta = MagicMock()
    delta.content = content
    choice = MagicMock()
    choice.delta = delta
    chunk = MagicMock()
    chunk.choices = [choice]
    return chunk


class _FakeStream:
    """Async iterator yielding pre-built fake chunks."""

    def __init__(self, chunks: list[MagicMock]) -> None:
        self._chunks = chunks

    def __aiter__(self) -> "_FakeStream":
        self._index = 0
        return self

    async def __anext__(self) -> MagicMock:
        if self._index >= len(self._chunks):
            raise StopAsyncIteration
        chunk = self._chunks[self._index]
        self._index += 1
        return chunk


def _make_api_status_error(status_code: int) -> APIStatusError:
    """Create a fake APIStatusError with the given status code."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {}
    return APIStatusError(
        message=f"HTTP {status_code}",
        response=resp,
        body=None,
    )


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_openai_client() -> MagicMock:
    """Patch AsyncOpenAI so no real network calls are made."""
    with patch("aria.api.openrouter.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        # Default: completions.create returns a valid response
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_chat_completion("Hello from OpenRouter!")
        )
        yield mock_client


# ── Constructor tests ─────────────────────────────────────────────────────────


class TestOpenRouterClientInit:
    """Tests for OpenRouterClient constructor."""

    def test_raises_on_empty_key(self, mock_openai_client: MagicMock) -> None:
        """Constructor raises APIError when api_key is empty string."""
        with pytest.raises(APIError, match="not configured"):
            OpenRouterClient(api_key="")

    def test_raises_on_whitespace_key(self, mock_openai_client: MagicMock) -> None:
        """Empty-string api_key (from env not set) raises APIError."""
        with pytest.raises(APIError):
            OpenRouterClient(api_key="")

    def test_default_model(self, mock_openai_client: MagicMock) -> None:
        """Default model is meta-llama/llama-3-70b-instruct."""
        client = OpenRouterClient(api_key="sk-or-test")
        assert client._model_name == "meta-llama/llama-3-70b-instruct"

    def test_custom_model(self, mock_openai_client: MagicMock) -> None:
        """Custom model name is stored correctly."""
        client = OpenRouterClient(api_key="sk-or-test", model_name="openai/gpt-4o")
        assert client._model_name == "openai/gpt-4o"


# ── send_message (non-streaming) ──────────────────────────────────────────────


class TestOpenRouterClientSendMessage:
    """Tests for OpenRouterClient.send_message."""

    @pytest.mark.asyncio
    async def test_returns_response_text(self, mock_openai_client: MagicMock) -> None:
        """send_message returns the assistant message content."""
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=_make_chat_completion("AI says hello")
        )
        client = OpenRouterClient(api_key="sk-or-test")
        result = await client.send_message([{"role": "user", "content": "Hi"}])
        assert result == "AI says hello"

    @pytest.mark.asyncio
    async def test_system_prompt_prepended(self, mock_openai_client: MagicMock) -> None:
        """System prompt is prepended as a system role message."""
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=_make_chat_completion("ok")
        )
        client = OpenRouterClient(api_key="sk-or-test")
        await client.send_message(
            [{"role": "user", "content": "Query"}],
            system_prompt="You are Aria.",
        )
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are Aria."
        assert messages[1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_raises_on_empty_messages(self, mock_openai_client: MagicMock) -> None:
        """send_message raises APIError when message list is empty."""
        client = OpenRouterClient(api_key="sk-or-test")
        with pytest.raises(APIError, match="empty"):
            await client.send_message([])

    @pytest.mark.asyncio
    async def test_raises_on_401(self, mock_openai_client: MagicMock) -> None:
        """send_message raises APIError immediately on 401."""
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=_make_api_status_error(401)
        )
        client = OpenRouterClient(api_key="sk-or-test")
        with pytest.raises(APIError, match="Invalid OpenRouter"):
            await client.send_message([{"role": "user", "content": "Hi"}])

    @pytest.mark.asyncio
    async def test_raises_on_timeout(self, mock_openai_client: MagicMock) -> None:
        """send_message raises APIError on timeout."""
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError(request=MagicMock())
        )
        client = OpenRouterClient(api_key="sk-or-test")
        with pytest.raises(APIError, match="timed out"):
            await client.send_message([{"role": "user", "content": "Hi"}])

    @pytest.mark.asyncio
    async def test_retries_on_429_then_succeeds(self, mock_openai_client: MagicMock) -> None:
        """send_message retries on 429 and eventually succeeds."""
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=[
                _make_api_status_error(429),
                _make_chat_completion("Success after retry"),
            ]
        )
        with patch("asyncio.sleep", new_callable=AsyncMock):
            client = OpenRouterClient(api_key="sk-or-test")
            result = await client.send_message([{"role": "user", "content": "Hi"}])
        assert result == "Success after retry"

    @pytest.mark.asyncio
    async def test_raises_after_all_retries_exhausted(
        self, mock_openai_client: MagicMock
    ) -> None:
        """send_message raises APIError after all retries fail (server error)."""
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=_make_api_status_error(503)
        )
        with patch("asyncio.sleep", new_callable=AsyncMock):
            client = OpenRouterClient(api_key="sk-or-test")
            with pytest.raises(APIError, match="temporarily unavailable"):
                await client.send_message([{"role": "user", "content": "Hi"}])


# ── send_message_stream ───────────────────────────────────────────────────────


class TestOpenRouterClientStream:
    """Tests for OpenRouterClient.send_message_stream."""

    async def _collect(self, gen: AsyncIterator[str]) -> list[str]:
        chunks: list[str] = []
        async for chunk in gen:
            chunks.append(chunk)
        return chunks

    @pytest.mark.asyncio
    async def test_yields_chunks(self, mock_openai_client: MagicMock) -> None:
        """send_message_stream yields text chunks from the SSE stream."""
        fake_chunks = [
            _make_stream_chunk("Hello"),
            _make_stream_chunk(" world"),
            _make_stream_chunk("!"),
        ]
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=_FakeStream(fake_chunks)
        )
        client = OpenRouterClient(api_key="sk-or-test")
        chunks = await self._collect(
            client.send_message_stream([{"role": "user", "content": "Hi"}])
        )
        assert chunks == ["Hello", " world", "!"]

    @pytest.mark.asyncio
    async def test_none_delta_yields_empty_string(self, mock_openai_client: MagicMock) -> None:
        """None delta.content is coerced to empty string, not raised."""
        fake_chunks = [
            _make_stream_chunk(None),
            _make_stream_chunk("text"),
        ]
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=_FakeStream(fake_chunks)
        )
        client = OpenRouterClient(api_key="sk-or-test")
        chunks = await self._collect(
            client.send_message_stream([{"role": "user", "content": "Hi"}])
        )
        assert chunks == ["", "text"]

    @pytest.mark.asyncio
    async def test_raises_on_empty_messages(self, mock_openai_client: MagicMock) -> None:
        """send_message_stream raises APIError when messages list is empty."""
        client = OpenRouterClient(api_key="sk-or-test")
        with pytest.raises(APIError, match="empty"):
            async for _ in client.send_message_stream([]):
                pass

    @pytest.mark.asyncio
    async def test_raises_on_401_stream(self, mock_openai_client: MagicMock) -> None:
        """send_message_stream raises APIError immediately on 401."""
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=_make_api_status_error(401)
        )
        client = OpenRouterClient(api_key="sk-or-test")
        with pytest.raises(APIError, match="Invalid OpenRouter"):
            async for _ in client.send_message_stream([{"role": "user", "content": "Hi"}]):
                pass

    @pytest.mark.asyncio
    async def test_retries_on_503_then_streams(self, mock_openai_client: MagicMock) -> None:
        """send_message_stream retries on 503 and eventually yields chunks."""
        fake_chunks = [_make_stream_chunk("OK")]
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=[
                _make_api_status_error(503),
                _FakeStream(fake_chunks),
            ]
        )
        with patch("asyncio.sleep", new_callable=AsyncMock):
            client = OpenRouterClient(api_key="sk-or-test")
            chunks = await self._collect(
                client.send_message_stream([{"role": "user", "content": "Hi"}])
            )
        assert chunks == ["OK"]


# ── validate_key ─────────────────────────────────────────────────────────────


class TestOpenRouterClientValidateKey:
    """Tests for OpenRouterClient.validate_key."""

    @pytest.mark.asyncio
    async def test_valid_key_returns_true(self, mock_openai_client: MagicMock) -> None:
        """validate_key returns True on HTTP 200."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": {"label": "test-key"}})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aria.api.openrouter.aiohttp.ClientSession", return_value=mock_session):
            client = OpenRouterClient(api_key="sk-or-test")
            result = await client.validate_key()
        assert result is True

    @pytest.mark.asyncio
    async def test_invalid_key_raises_api_error(self, mock_openai_client: MagicMock) -> None:
        """validate_key raises APIError on HTTP 401."""
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aria.api.openrouter.aiohttp.ClientSession", return_value=mock_session):
            client = OpenRouterClient(api_key="sk-or-bad")
            with pytest.raises(APIError, match="Invalid OpenRouter"):
                await client.validate_key()


# ── create_llm_client factory ─────────────────────────────────────────────────


class TestCreateLlmClientFactory:
    """Tests for the create_llm_client factory function."""

    def test_creates_gemini_client(self) -> None:
        """create_llm_client returns a GeminiClient for provider='gemini'."""
        from aria.api.gemini import GeminiClient

        with patch("aria.api.gemini.genai.Client"):
            client = create_llm_client(
                provider="gemini",
                model_name="gemini-1.5-pro",
                gemini_api_key="test-gemini-key",
            )
        assert isinstance(client, GeminiClient)

    def test_creates_openrouter_client(self, mock_openai_client: MagicMock) -> None:
        """create_llm_client returns an OpenRouterClient for provider='openrouter'."""
        client = create_llm_client(
            provider="openrouter",
            model_name="openai/gpt-4o",
            openrouter_api_key="sk-or-test",
        )
        assert isinstance(client, OpenRouterClient)
        assert client._model_name == "openai/gpt-4o"

    def test_raises_on_unknown_provider(self) -> None:
        """create_llm_client raises ValueError for an unknown provider string."""
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_llm_client(provider="anthropic", model_name="claude-3")

    def test_raises_on_missing_gemini_key(self) -> None:
        """create_llm_client raises APIError when Gemini key is empty."""
        with patch("aria.api.gemini.genai.Client"):
            with pytest.raises(APIError, match="not configured"):
                create_llm_client(
                    provider="gemini",
                    model_name="gemini-1.5-pro",
                    gemini_api_key="",
                )

    def test_raises_on_missing_openrouter_key(self, mock_openai_client: MagicMock) -> None:
        """create_llm_client raises APIError when OpenRouter key is empty."""
        with pytest.raises(APIError, match="not configured"):
            create_llm_client(
                provider="openrouter",
                model_name="openai/gpt-4o",
                openrouter_api_key="",
            )

    def test_openrouter_model_name_forwarded(self, mock_openai_client: MagicMock) -> None:
        """create_llm_client correctly forwards the model_name to OpenRouterClient."""
        client = create_llm_client(
            provider="openrouter",
            model_name="anthropic/claude-3.5-sonnet",
            openrouter_api_key="sk-or-test",
        )
        assert isinstance(client, OpenRouterClient)
        assert client._model_name == "anthropic/claude-3.5-sonnet"
