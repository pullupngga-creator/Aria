"""Unit tests for chat history persistence (conversations and messages)."""

import sqlite3
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest

from aria.chat import history as chat_history
from aria.db.migrations import init_schema


class NoCloseConnection:
    """Wrapper around a sqlite3.Connection that makes close() a no-op.

    This allows history functions to call get_connection()/close() without
    destroying the shared in-memory database used across multiple calls.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def close(self) -> None:
        pass  # Intentionally a no-op

    def cursor(self) -> sqlite3.Cursor:
        return self._conn.cursor()

    def execute(self, *args: Any, **kwargs: Any) -> sqlite3.Cursor:
        return self._conn.execute(*args, **kwargs)

    def commit(self) -> None:
        self._conn.commit()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)


@pytest.fixture()
def db_conn() -> Generator[sqlite3.Connection, None, None]:
    """Provide an in-memory SQLite connection with the Aria schema applied.

    Patches ``aria.db.connection.get_connection`` so all history module calls
    use this in-memory database for the duration of the test.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)

    wrapped = NoCloseConnection(conn)
    with patch("aria.chat.history.get_connection", return_value=wrapped):
        yield conn

    conn.close()


class TestCreateConversation:
    """Tests for create_conversation()."""

    def test_returns_uuid(self, db_conn: sqlite3.Connection) -> None:
        """create_conversation returns a valid UUID string."""
        conv_id = chat_history.create_conversation("gemini", "gemini-1.5-pro")
        assert len(conv_id) == 36  # UUID v4 format
        assert "-" in conv_id

    def test_inserts_row(self, db_conn: sqlite3.Connection) -> None:
        """create_conversation inserts a row into the conversations table."""
        conv_id = chat_history.create_conversation(
            "gemini", "gemini-1.5-pro", title="Test Chat"
        )
        cursor = db_conn.cursor()
        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["title"] == "Test Chat"
        assert row["model_provider"] == "gemini"
        assert row["model_name"] == "gemini-1.5-pro"

    def test_default_title(self, db_conn: sqlite3.Connection) -> None:
        """Default title is 'New Chat' when not specified."""
        conv_id = chat_history.create_conversation("gemini", "gemini-1.5-pro")
        cursor = db_conn.cursor()
        cursor.execute("SELECT title FROM conversations WHERE id = ?", (conv_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["title"] == "New Chat"


class TestSaveMessage:
    """Tests for save_message()."""

    def test_returns_uuid(self, db_conn: sqlite3.Connection) -> None:
        """save_message returns a valid UUID string."""
        conv_id = chat_history.create_conversation("gemini", "gemini-1.5-pro")
        msg_id = chat_history.save_message(conv_id, "user", "Hello Aria!")
        assert len(msg_id) == 36

    def test_inserts_user_message(self, db_conn: sqlite3.Connection) -> None:
        """save_message correctly stores a user message."""
        conv_id = chat_history.create_conversation("gemini", "gemini-1.5-pro")
        msg_id = chat_history.save_message(
            conversation_id=conv_id,
            role="user",
            content="What is machine learning?",
            token_count=5,
        )
        cursor = db_conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["role"] == "user"
        assert row["content"] == "What is machine learning?"
        assert row["token_count"] == 5

    def test_inserts_assistant_message(self, db_conn: sqlite3.Connection) -> None:
        """save_message correctly stores an assistant message with model info."""
        conv_id = chat_history.create_conversation("gemini", "gemini-1.5-pro")
        msg_id = chat_history.save_message(
            conversation_id=conv_id,
            role="assistant",
            content="Machine learning is a subset of AI...",
            token_count=12,
            model_provider="gemini",
            model_name="gemini-1.5-pro",
        )
        cursor = db_conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["role"] == "assistant"
        assert row["model_provider"] == "gemini"
        assert row["model_name"] == "gemini-1.5-pro"

    def test_updates_conversation_timestamp(self, db_conn: sqlite3.Connection) -> None:
        """Saving a message updates the conversation's updated_at."""
        conv_id = chat_history.create_conversation("gemini", "gemini-1.5-pro")
        cursor = db_conn.cursor()
        cursor.execute("SELECT updated_at FROM conversations WHERE id = ?", (conv_id,))
        before = cursor.fetchone()["updated_at"]

        chat_history.save_message(conv_id, "user", "Hello")

        cursor.execute("SELECT updated_at FROM conversations WHERE id = ?", (conv_id,))
        after = cursor.fetchone()["updated_at"]
        # updated_at should be same or later (ISO string comparison)
        assert after >= before


class TestGetMessages:
    """Tests for get_messages()."""

    def test_returns_messages_in_order(self, db_conn: sqlite3.Connection) -> None:
        """Messages are returned in chronological order."""
        conv_id = chat_history.create_conversation("gemini", "gemini-1.5-pro")
        chat_history.save_message(conv_id, "user", "First message")
        chat_history.save_message(conv_id, "assistant", "First response")
        chat_history.save_message(conv_id, "user", "Second message")

        messages = chat_history.get_messages(conv_id)
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "First message"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["content"] == "Second message"

    def test_returns_empty_for_new_conversation(self, db_conn: sqlite3.Connection) -> None:
        """A new conversation has no messages."""
        conv_id = chat_history.create_conversation("gemini", "gemini-1.5-pro")
        messages = chat_history.get_messages(conv_id)
        assert messages == []

    def test_message_dict_keys(self, db_conn: sqlite3.Connection) -> None:
        """Returned message dicts have all expected keys."""
        conv_id = chat_history.create_conversation("gemini", "gemini-1.5-pro")
        chat_history.save_message(conv_id, "user", "Test")
        messages = chat_history.get_messages(conv_id)
        msg = messages[0]
        expected_keys = {
            "id", "conversation_id", "role", "content", "sources_used",
            "token_count", "model_provider", "model_name", "created_at",
        }
        assert set(msg.keys()) == expected_keys


class TestGetConversations:
    """Tests for get_conversations()."""

    def test_returns_non_archived(self, db_conn: sqlite3.Connection) -> None:
        """Only non-archived conversations are returned."""
        chat_history.create_conversation("gemini", "gemini-1.5-pro", title="Active")
        # Manually archive one
        archived_id = chat_history.create_conversation(
            "gemini", "gemini-1.5-pro", title="Archived"
        )
        db_conn.execute(
            "UPDATE conversations SET is_archived = 1 WHERE id = ?", (archived_id,)
        )
        db_conn.commit()

        conversations = chat_history.get_conversations()
        assert len(conversations) == 1
        assert conversations[0]["title"] == "Active"

    def test_ordered_by_updated_desc(self, db_conn: sqlite3.Connection) -> None:
        """Conversations are ordered by most recently updated first."""
        id1 = chat_history.create_conversation("gemini", "gemini-1.5-pro", title="First")
        id2 = chat_history.create_conversation("gemini", "gemini-1.5-pro", title="Second")

        # Make id1 more recent by updating it
        chat_history.save_message(id1, "user", "latest")

        conversations = chat_history.get_conversations()
        assert len(conversations) == 2
        assert conversations[0]["title"] == "First"  # Most recently updated


class TestUpdateConversationTitle:
    """Tests for update_conversation_title()."""

    def test_updates_title(self, db_conn: sqlite3.Connection) -> None:
        """Title is updated correctly."""
        conv_id = chat_history.create_conversation("gemini", "gemini-1.5-pro")
        chat_history.update_conversation_title(conv_id, "Renamed Chat")

        cursor = db_conn.cursor()
        cursor.execute("SELECT title FROM conversations WHERE id = ?", (conv_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["title"] == "Renamed Chat"


class TestDeleteConversation:
    """Tests for delete_conversation()."""

    def test_cascade_deletes_messages(self, db_conn: sqlite3.Connection) -> None:
        """Deleting a conversation also deletes its messages (FK CASCADE)."""
        conv_id = chat_history.create_conversation("gemini", "gemini-1.5-pro")
        chat_history.save_message(conv_id, "user", "Hello")
        chat_history.save_message(conv_id, "assistant", "Hi")

        chat_history.delete_conversation(conv_id)

        cursor = db_conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = ?", (conv_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["cnt"] == 0

    def test_conversation_removed(self, db_conn: sqlite3.Connection) -> None:
        """Conversation row is removed after deletion."""
        conv_id = chat_history.create_conversation("gemini", "gemini-1.5-pro")
        chat_history.delete_conversation(conv_id)

        cursor = db_conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM conversations WHERE id = ?", (conv_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["cnt"] == 0
