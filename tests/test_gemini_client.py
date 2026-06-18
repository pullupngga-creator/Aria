"""Unit tests for the GeminiClient (API layer)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai.errors import ClientError, ServerError

from aria.api.gemini import GeminiClient
from aria.exceptions import APIError


class FakeResponse:
    """Fake Gemini API response object."""

    def __init__(self, text: str = "Hello from Gemini!") -> None:
        self.text = text


def _make_client_error(code: int, message: str = "error") -> ClientError:
    """Helper to create a ClientError with a given status code."""
    return ClientError(code, {"error": {"message": message}}, None)


@pytest.fixture()
def mock_genai_client() -> MagicMock:
    """Patch genai.Client so no real API calls are made."""
    with patch("aria.api.gemini.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        # Default: generate_content returns a valid response
        mock_client.aio.models.generate_content = AsyncMock(
            return_value=FakeResponse("AI reply here"),
        )
        yield mock_client


class TestGeminiClientInit:
    """Tests for GeminiClient constructor."""

    def test_raises_on_empty_key(self, mock_genai_client: MagicMock) -> None:
        """Constructor raises APIError when api_key is empty."""
        with pytest.raises(APIError, match="not configured"):
            GeminiClient(api_key="")

    def test_initializes_with_valid_key(self, mock_genai_client: MagicMock) -> None:
        """Constructor creates a genai.Client with the given API key."""
        client = GeminiClient(api_key="test-key-123")
        assert client._model_name == "gemini-1.5-pro"
        assert client._client is mock_genai_client

    def test_custom_model_name(self, mock_genai_client: MagicMock) -> None:
        """Constructor accepts a custom model name."""
        client = GeminiClient(api_key="key", model_name="gemini-1.5-flash")
        assert client._model_name == "gemini-1.5-flash"


class TestSendMessage:
    """Tests for GeminiClient.send_message()."""

    @pytest.mark.asyncio
    async def test_returns_response_text(self, mock_genai_client: MagicMock) -> None:
        """send_message returns the response text from Gemini."""
        mock_genai_client.aio.models.generate_content = AsyncMock(
            return_value=FakeResponse("AI reply here"),
        )

        client = GeminiClient(api_key="test-key")
        result = await client.send_message(
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert result == "AI reply here"

    @pytest.mark.asyncio
    async def test_empty_messages_raises(self, mock_genai_client: MagicMock) -> None:
        """send_message raises APIError for an empty message list."""
        client = GeminiClient(api_key="test-key")

        with pytest.raises(APIError, match="empty message list"):
            await client.send_message(messages=[])

    @pytest.mark.asyncio
    async def test_passes_system_prompt(self, mock_genai_client: MagicMock) -> None:
        """System prompt is passed via GenerateContentConfig."""
        mock_genai_client.aio.models.generate_content = AsyncMock(
            return_value=FakeResponse("ok"),
        )

        client = GeminiClient(api_key="test-key")
        await client.send_message(
            messages=[{"role": "user", "content": "Hi"}],
            system_prompt="You are a helpful bot.",
        )
        call_kwargs = mock_genai_client.aio.models.generate_content.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config is not None
        assert config.system_instruction == "You are a helpful bot."

    @pytest.mark.asyncio
    async def test_converts_history_roles(self, mock_genai_client: MagicMock) -> None:
        """Aria 'assistant' role is mapped to Gemini 'model' role."""
        mock_genai_client.aio.models.generate_content = AsyncMock(
            return_value=FakeResponse("ok"),
        )

        client = GeminiClient(api_key="test-key")
        await client.send_message(
            messages=[
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"},
                {"role": "user", "content": "How are you?"},
            ]
        )
        call_kwargs = mock_genai_client.aio.models.generate_content.call_args
        contents = call_kwargs.kwargs.get("contents") or call_kwargs[1].get("contents")
        # 3 contents: user "Hi", model "Hello!", user "How are you?"
        assert len(contents) == 3
        assert contents[0].role == "user"
        assert contents[1].role == "model"
        assert contents[2].role == "user"

    @pytest.mark.asyncio
    async def test_empty_response_fallback(self, mock_genai_client: MagicMock) -> None:
        """Returns 'No response generated' when response.text is empty."""
        mock_genai_client.aio.models.generate_content = AsyncMock(
            return_value=FakeResponse(text=""),
        )

        client = GeminiClient(api_key="test-key")
        result = await client.send_message(
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert result == "No response generated"

    @pytest.mark.asyncio
    async def test_timeout_raises_api_error(self, mock_genai_client: MagicMock) -> None:
        """TimeoutError is converted to APIError with a friendly message."""
        mock_genai_client.aio.models.generate_content = AsyncMock(
            side_effect=TimeoutError(),
        )

        client = GeminiClient(api_key="test-key", timeout=0.1)
        with pytest.raises(APIError, match="timed out"):
            await client.send_message(
                messages=[{"role": "user", "content": "Hello"}],
            )

    @pytest.mark.asyncio
    async def test_retries_on_server_error(self, mock_genai_client: MagicMock) -> None:
        """Retries on ServerError (503) and succeeds on second attempt."""
        call_count = 0

        async def side_effect(**kwargs: object) -> FakeResponse:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ServerError(503, {"error": {"message": "unavailable"}}, None)
            return FakeResponse("Success after retry")

        mock_genai_client.aio.models.generate_content = AsyncMock(
            side_effect=side_effect,
        )

        client = GeminiClient(api_key="test-key")
        # Patch backoff to avoid slow tests
        with patch("aria.api.gemini._BACKOFF_SECONDS", [0.0, 0.0, 0.0]):
            result = await client.send_message(
                messages=[{"role": "user", "content": "Hello"}],
            )
        assert result == "Success after retry"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises(self, mock_genai_client: MagicMock) -> None:
        """APIError is raised after all retries are exhausted."""
        mock_genai_client.aio.models.generate_content = AsyncMock(
            side_effect=ServerError(503, {"error": {"message": "down"}}, None),
        )

        client = GeminiClient(api_key="test-key")
        with patch("aria.api.gemini._BACKOFF_SECONDS", [0.0, 0.0, 0.0]):
            with pytest.raises(APIError, match="temporarily unavailable"):
                await client.send_message(
                    messages=[{"role": "user", "content": "Hello"}],
                )

    @pytest.mark.asyncio
    async def test_invalid_key_raises(self, mock_genai_client: MagicMock) -> None:
        """ClientError with 401 raises APIError about invalid key."""
        mock_genai_client.aio.models.generate_content = AsyncMock(
            side_effect=_make_client_error(401, "bad key"),
        )

        client = GeminiClient(api_key="bad-key")
        with pytest.raises(APIError, match="Invalid Gemini API key"):
            await client.send_message(
                messages=[{"role": "user", "content": "Hello"}],
            )


class TestValidateKey:
    """Tests for GeminiClient.validate_key()."""

    @pytest.mark.asyncio
    async def test_valid_key_returns_true(self, mock_genai_client: MagicMock) -> None:
        """validate_key returns True when key is valid."""

        class FakePager:
            def __aiter__(self) -> "FakePager":
                return self

            async def __anext__(self) -> None:
                raise StopAsyncIteration

        mock_genai_client.aio.models.list = AsyncMock(return_value=FakePager())

        client = GeminiClient(api_key="valid-key")
        result = await client.validate_key()
        assert result is True

    @pytest.mark.asyncio
    async def test_invalid_key_raises(self, mock_genai_client: MagicMock) -> None:
        """validate_key raises APIError on 401 ClientError."""
        mock_genai_client.aio.models.list = AsyncMock(
            side_effect=_make_client_error(401, "bad key"),
        )

        client = GeminiClient(api_key="bad-key")
        with pytest.raises(APIError, match="Invalid Gemini API key"):
            await client.validate_key()
