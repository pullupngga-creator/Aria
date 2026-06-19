"""Unit tests for chat history persistence (conversations and messages) — async."""

import sqlite3
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import aiosqlite
import pytest

from aria.chat import history as chat_history
from aria.db.migrations import init_schema


class NoCloseAsyncConnection:
    """Wrapper around an aiosqlite.Connection that makes close() a no-op.

    This allows history functions to call get_async_connection()/close()
    without destroying the shared in-memory database used across tests.
    Attribute access is forwarded to the underlying aiosqlite connection.
    """

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def close(self) -> None:
        pass  # Intentionally a no-op

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)


@pytest.fixture()
async def db_conn() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Provide an async aiosqlite connection with the Aria schema applied.

    Uses a temporary file so that:
    1. The schema can be applied synchronously via the existing migration module.
    2. An async aiosqlite connection can then be opened on the same file.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Apply schema synchronously (migrations use stdlib sqlite3)
        sync_conn = sqlite3.connect(str(db_path))
        sync_conn.row_factory = sqlite3.Row
        sync_conn.execute("PRAGMA foreign_keys = ON")
        init_schema(sync_conn)
        sync_conn.close()

        # Open async connection for the test
        async_conn = await aiosqlite.connect(str(db_path))
        async_conn.row_factory = aiosqlite.Row  # type: ignore[assignment]
        await async_conn.execute("PRAGMA foreign_keys = ON")

        wrapped = NoCloseAsyncConnection(async_conn)

        from unittest.mock import patch

        with patch("aria.chat.history.get_async_connection", return_value=wrapped):
            yield async_conn

        await async_conn.close()


class TestCreateConversation:
    """Tests for create_conversation()."""

    async def test_returns_uuid(self, db_conn: aiosqlite.Connection) -> None:
        """create_conversation returns a valid UUID string."""
        conv_id = await chat_history.create_conversation("gemini", "gemini-1.5-pro")
        assert len(conv_id) == 36  # UUID v4 format
        assert "-" in conv_id

    async def test_inserts_row(self, db_conn: aiosqlite.Connection) -> None:
        """create_conversation inserts a row into the conversations table."""
        conv_id = await chat_history.create_conversation(
            "gemini", "gemini-1.5-pro", title="Test Chat"
        )
        cursor = await db_conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["title"] == "Test Chat"
        assert row["model_provider"] == "gemini"
        assert row["model_name"] == "gemini-1.5-pro"

    async def test_default_title(self, db_conn: aiosqlite.Connection) -> None:
        """Default title is 'New Chat' when not specified."""
        conv_id = await chat_history.create_conversation("gemini", "gemini-1.5-pro")
        cursor = await db_conn.execute(
            "SELECT title FROM conversations WHERE id = ?", (conv_id,)
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["title"] == "New Chat"


class TestSaveMessage:
    """Tests for save_message()."""

    async def test_returns_tuple(self, db_conn: aiosqlite.Connection) -> None:
        """save_message returns a (message_id, created_at) tuple."""
        conv_id = await chat_history.create_conversation("gemini", "gemini-1.5-pro")
        result = await chat_history.save_message(conv_id, "user", "Hello Aria!")
        assert isinstance(result, tuple)
        assert len(result) == 2
        msg_id, created_at = result
        assert len(msg_id) == 36
        assert created_at  # non-empty ISO timestamp

    async def test_inserts_user_message(self, db_conn: aiosqlite.Connection) -> None:
        """save_message correctly stores a user message."""
        conv_id = await chat_history.create_conversation("gemini", "gemini-1.5-pro")
        msg_id, _ = await chat_history.save_message(
            conversation_id=conv_id,
            role="user",
            content="What is machine learning?",
            token_count=5,
        )
        cursor = await db_conn.execute(
            "SELECT * FROM messages WHERE id = ?", (msg_id,)
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["role"] == "user"
        assert row["content"] == "What is machine learning?"
        assert row["token_count"] == 5

    async def test_inserts_assistant_message(self, db_conn: aiosqlite.Connection) -> None:
        """save_message correctly stores an assistant message with model info."""
        conv_id = await chat_history.create_conversation("gemini", "gemini-1.5-pro")
        msg_id, _ = await chat_history.save_message(
            conversation_id=conv_id,
            role="assistant",
            content="Machine learning is a subset of AI...",
            token_count=12,
            model_provider="gemini",
            model_name="gemini-1.5-pro",
        )
        cursor = await db_conn.execute(
            "SELECT * FROM messages WHERE id = ?", (msg_id,)
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["role"] == "assistant"
        assert row["model_provider"] == "gemini"
        assert row["model_name"] == "gemini-1.5-pro"

    async def test_updates_conversation_timestamp(
        self, db_conn: aiosqlite.Connection
    ) -> None:
        """Saving a message updates the conversation's updated_at."""
        conv_id = await chat_history.create_conversation("gemini", "gemini-1.5-pro")
        cursor = await db_conn.execute(
            "SELECT updated_at FROM conversations WHERE id = ?", (conv_id,)
        )
        row_before = await cursor.fetchone()
        assert row_before is not None
        before = row_before["updated_at"]

        await chat_history.save_message(conv_id, "user", "Hello")

        cursor = await db_conn.execute(
            "SELECT updated_at FROM conversations WHERE id = ?", (conv_id,)
        )
        row_after = await cursor.fetchone()
        assert row_after is not None
        after = row_after["updated_at"]
        # updated_at should be same or later (ISO string comparison)
        assert after >= before


class TestGetMessages:
    """Tests for get_messages()."""

    async def test_returns_messages_in_order(
        self, db_conn: aiosqlite.Connection
    ) -> None:
        """Messages are returned in chronological order."""
        conv_id = await chat_history.create_conversation("gemini", "gemini-1.5-pro")
        await chat_history.save_message(conv_id, "user", "First message")
        await chat_history.save_message(conv_id, "assistant", "First response")
        await chat_history.save_message(conv_id, "user", "Second message")

        messages = await chat_history.get_messages(conv_id)
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "First message"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["content"] == "Second message"

    async def test_returns_empty_for_new_conversation(
        self, db_conn: aiosqlite.Connection
    ) -> None:
        """A new conversation has no messages."""
        conv_id = await chat_history.create_conversation("gemini", "gemini-1.5-pro")
        messages = await chat_history.get_messages(conv_id)
        assert messages == []

    async def test_message_dict_keys(self, db_conn: aiosqlite.Connection) -> None:
        """Returned message dicts have all expected keys."""
        conv_id = await chat_history.create_conversation("gemini", "gemini-1.5-pro")
        await chat_history.save_message(conv_id, "user", "Test")
        messages = await chat_history.get_messages(conv_id)
        msg = messages[0]
        expected_keys = {
            "id", "conversation_id", "role", "content", "sources_used",
            "token_count", "model_provider", "model_name", "created_at",
        }
        assert set(msg.keys()) == expected_keys

    async def test_messages_have_timestamps(self, db_conn: aiosqlite.Connection) -> None:
        """Returned message dicts include a non-empty created_at timestamp."""
        conv_id = await chat_history.create_conversation("gemini", "gemini-1.5-pro")
        await chat_history.save_message(conv_id, "user", "Hello")
        messages = await chat_history.get_messages(conv_id)
        assert messages[0]["created_at"]  # non-empty string


class TestGetConversations:
    """Tests for get_conversations()."""

    async def test_returns_non_archived(self, db_conn: aiosqlite.Connection) -> None:
        """Only non-archived conversations are returned."""
        await chat_history.create_conversation("gemini", "gemini-1.5-pro", title="Active")
        # Manually archive one
        archived_id = await chat_history.create_conversation(
            "gemini", "gemini-1.5-pro", title="Archived"
        )
        await db_conn.execute(
            "UPDATE conversations SET is_archived = 1 WHERE id = ?", (archived_id,)
        )
        await db_conn.commit()

        conversations = await chat_history.get_conversations()
        assert len(conversations) == 1
        assert conversations[0]["title"] == "Active"

    async def test_ordered_by_updated_desc(
        self, db_conn: aiosqlite.Connection
    ) -> None:
        """Conversations are ordered by most recently updated first."""
        id1 = await chat_history.create_conversation(
            "gemini", "gemini-1.5-pro", title="First"
        )
        await chat_history.create_conversation(
            "gemini", "gemini-1.5-pro", title="Second"
        )

        # Make id1 more recent by updating it
        await chat_history.save_message(id1, "user", "latest")

        conversations = await chat_history.get_conversations()
        assert len(conversations) == 2
        assert conversations[0]["title"] == "First"  # Most recently updated


class TestUpdateConversationTitle:
    """Tests for update_conversation_title()."""

    async def test_updates_title(self, db_conn: aiosqlite.Connection) -> None:
        """Title is updated correctly."""
        conv_id = await chat_history.create_conversation("gemini", "gemini-1.5-pro")
        await chat_history.update_conversation_title(conv_id, "Renamed Chat")

        cursor = await db_conn.execute(
            "SELECT title FROM conversations WHERE id = ?", (conv_id,)
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["title"] == "Renamed Chat"


class TestDeleteConversation:
    """Tests for delete_conversation()."""

    async def test_cascade_deletes_messages(
        self, db_conn: aiosqlite.Connection
    ) -> None:
        """Deleting a conversation also deletes its messages (FK CASCADE)."""
        conv_id = await chat_history.create_conversation("gemini", "gemini-1.5-pro")
        await chat_history.save_message(conv_id, "user", "Hello")
        await chat_history.save_message(conv_id, "assistant", "Hi")

        await chat_history.delete_conversation(conv_id)

        cursor = await db_conn.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = ?",
            (conv_id,),
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["cnt"] == 0

    async def test_conversation_removed(self, db_conn: aiosqlite.Connection) -> None:
        """Conversation row is removed after deletion."""
        conv_id = await chat_history.create_conversation("gemini", "gemini-1.5-pro")
        await chat_history.delete_conversation(conv_id)

        cursor = await db_conn.execute(
            "SELECT COUNT(*) as cnt FROM conversations WHERE id = ?", (conv_id,)
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["cnt"] == 0


class TestGetConversation:
    """Tests for get_conversation()."""

    async def test_returns_conversation(self, db_conn: aiosqlite.Connection) -> None:
        """get_conversation returns a dict for an existing conversation."""
        conv_id = await chat_history.create_conversation(
            "gemini", "gemini-1.5-pro", title="My Chat"
        )
        conv = await chat_history.get_conversation(conv_id)
        assert conv is not None
        assert conv["id"] == conv_id
        assert conv["title"] == "My Chat"
        assert conv["model_provider"] == "gemini"
        assert conv["model_name"] == "gemini-1.5-pro"

    async def test_returns_none_for_missing(
        self, db_conn: aiosqlite.Connection
    ) -> None:
        """get_conversation returns None for a non-existent ID."""
        conv = await chat_history.get_conversation("nonexistent-uuid")
        assert conv is None

    async def test_dict_keys(self, db_conn: aiosqlite.Connection) -> None:
        """Returned dict has all expected columns."""
        conv_id = await chat_history.create_conversation("gemini", "gemini-1.5-pro")
        conv = await chat_history.get_conversation(conv_id)
        assert conv is not None
        expected_keys = {
            "id", "title", "model_provider", "model_name",
            "system_prompt", "created_at", "updated_at", "is_archived",
        }
        assert set(conv.keys()) == expected_keys

    async def test_reflects_title_update(
        self, db_conn: aiosqlite.Connection
    ) -> None:
        """get_conversation reflects a title update."""
        conv_id = await chat_history.create_conversation("gemini", "gemini-1.5-pro")
        await chat_history.update_conversation_title(conv_id, "Updated Title")
        conv = await chat_history.get_conversation(conv_id)
        assert conv is not None
        assert conv["title"] == "Updated Title"
