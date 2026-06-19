"""SQLite CRUD operations for conversations and messages (async)."""

import logging
import uuid
from datetime import UTC, datetime

import aiosqlite

from aria.db.connection import get_async_connection

logger = logging.getLogger(__name__)


async def create_conversation(
    model_provider: str,
    model_name: str,
    title: str = "New Chat",
    system_prompt: str | None = None,
) -> str:
    """Create a new conversation record.

    Args:
        model_provider: LLM provider identifier (e.g., 'gemini').
        model_name: Model identifier (e.g., 'gemini-1.5-pro').
        title: Conversation title (defaults to 'New Chat').
        system_prompt: Optional custom system prompt override.

    Returns:
        UUID of the newly created conversation.
    """
    conversation_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    db = await get_async_connection()
    try:
        await db.execute(
            """
            INSERT INTO conversations (
                id, title, model_provider, model_name,
                system_prompt, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, title, model_provider, model_name, system_prompt, now, now),
        )
        await db.commit()
        logger.info("Conversation created", extra={"conversation_id": conversation_id})
        return conversation_id
    except aiosqlite.Error:
        logger.error("Failed to create conversation", exc_info=True)
        raise
    finally:
        await db.close()


async def save_message(
    conversation_id: str,
    role: str,
    content: str,
    sources_used: str | None = None,
    token_count: int = 0,
    model_provider: str | None = None,
    model_name: str | None = None,
) -> tuple[str, str]:
    """Save a message to a conversation.

    Also updates the conversation's updated_at timestamp.

    Args:
        conversation_id: UUID of the parent conversation.
        role: Message role ('user', 'assistant', 'system').
        content: Raw message text (Markdown).
        sources_used: JSON array string of document IDs referenced.
        token_count: Approximate token count of the content.
        model_provider: Provider used for this response (assistant only).
        model_name: Model used for this response (assistant only).

    Returns:
        Tuple of (message_id, created_at) for the newly created message.
    """
    message_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    db = await get_async_connection()
    try:
        await db.execute(
            """
            INSERT INTO messages (
                id, conversation_id, role, content, sources_used,
                token_count, model_provider, model_name, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                conversation_id,
                role,
                content,
                sources_used,
                token_count,
                model_provider,
                model_name,
                now,
            ),
        )
        # Update conversation timestamp
        await db.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        await db.commit()
        logger.info(
            "Message saved",
            extra={"message_id": message_id, "role": role, "conversation_id": conversation_id},
        )
        return message_id, now
    except aiosqlite.Error:
        logger.error("Failed to save message", exc_info=True)
        raise
    finally:
        await db.close()


async def get_messages(conversation_id: str) -> list[dict[str, str | int | None]]:
    """Retrieve all messages for a conversation, ordered chronologically.

    Args:
        conversation_id: UUID of the conversation.

    Returns:
        List of message dicts with all columns.
    """
    db = await get_async_connection()
    try:
        cursor = await db.execute(
            """
            SELECT id, conversation_id, role, content, sources_used,
                   token_count, model_provider, model_name, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            (conversation_id,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "conversation_id": row["conversation_id"],
                "role": row["role"],
                "content": row["content"],
                "sources_used": row["sources_used"],
                "token_count": int(row["token_count"] or 0),
                "model_provider": row["model_provider"],
                "model_name": row["model_name"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    finally:
        await db.close()


async def get_conversations() -> list[dict[str, str | int | None]]:
    """Retrieve all non-archived conversations, most recently updated first.

    Returns:
        List of conversation dicts with all columns.
    """
    db = await get_async_connection()
    try:
        cursor = await db.execute(
            """
            SELECT id, title, model_provider, model_name, system_prompt,
                   created_at, updated_at, is_archived
            FROM conversations
            WHERE is_archived = 0
            ORDER BY updated_at DESC
            """
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "model_provider": row["model_provider"],
                "model_name": row["model_name"],
                "system_prompt": row["system_prompt"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "is_archived": bool(int(row["is_archived"] or 0)),
            }
            for row in rows
        ]
    finally:
        await db.close()


async def update_conversation_title(conversation_id: str, title: str) -> None:
    """Update the title of a conversation.

    Args:
        conversation_id: UUID of the conversation.
        title: New title text.
    """
    db = await get_async_connection()
    try:
        await db.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, datetime.now(UTC).isoformat(), conversation_id),
        )
        await db.commit()
        logger.info("Conversation title updated", extra={"conversation_id": conversation_id})
    finally:
        await db.close()


async def get_conversation(conversation_id: str) -> dict[str, str | int | None] | None:
    """Retrieve a single conversation by its ID.

    Args:
        conversation_id: UUID of the conversation.

    Returns:
        Conversation dict with all columns, or None if not found.
    """
    db = await get_async_connection()
    try:
        cursor = await db.execute(
            """
            SELECT id, title, model_provider, model_name, system_prompt,
                   created_at, updated_at, is_archived
            FROM conversations
            WHERE id = ?
            """,
            (conversation_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "title": row["title"],
            "model_provider": row["model_provider"],
            "model_name": row["model_name"],
            "system_prompt": row["system_prompt"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "is_archived": bool(int(row["is_archived"] or 0)),
        }
    finally:
        await db.close()


async def delete_conversation(conversation_id: str) -> None:
    """Delete a conversation and all its messages (via CASCADE).

    Args:
        conversation_id: UUID of the conversation to delete.
    """
    db = await get_async_connection()
    try:
        await db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        await db.commit()
        logger.info("Conversation deleted", extra={"conversation_id": conversation_id})
    finally:
        await db.close()
