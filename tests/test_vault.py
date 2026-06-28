"""Unit tests for VaultManager."""

import sqlite3
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import aiosqlite
import pytest

from aria.db.migrations import init_schema
from aria.document.vault import VaultManager, _VAULT_DIR
from aria.exceptions import UnsupportedFileTypeError


class NoCloseAsyncConnection:
    """Wrapper around an aiosqlite.Connection that makes close() a no-op."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def close(self) -> None:
        pass  # Intentionally a no-op

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)


@pytest.fixture()
async def temp_vault_env() -> AsyncGenerator[tuple[Path, aiosqlite.Connection], None]:
    """Sets up a temporary vault directory and database connection for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "test.db"
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir(parents=True, exist_ok=True)

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

        with patch("aria.document.vault._VAULT_DIR", vault_dir), \
             patch("aria.document.vault.get_async_connection", return_value=wrapped):
            yield vault_dir, async_conn

        await async_conn.close()


@pytest.mark.asyncio
async def test_upload_document_success(
    temp_vault_env: tuple[Path, aiosqlite.Connection], tmp_path: Path
) -> None:
    """Test that upload_document successfully processes, database-inserts, and stores a document."""
    vault_dir, db = temp_vault_env
    vault_manager = VaultManager()

    # Create a mock source document
    source_file = tmp_path / "document.docx"
    
    # We can create a simple docx or just a txt, since allowed extensions include txt and docx.
    # Let's write a simple txt file first
    source_txt = tmp_path / "test.txt"
    source_txt.write_text("Hello parsing world! This is a test file.", encoding="utf-8")

    metadata = await vault_manager.upload_document(source_txt)
    
    assert metadata.filename == "test.txt"
    assert metadata.file_type == "txt"
    assert metadata.word_count == 8
    assert metadata.token_count > 0
    assert metadata.extracted_text == "Hello parsing world! This is a test file."
    
    # Verify database entry
    async with db.execute("SELECT * FROM documents WHERE id = ?", (metadata.id,)) as cursor:
        row = await cursor.fetchone()
        assert row is not None
        assert row["filename"] == "test.txt"
        assert row["file_type"] == "txt"
        assert row["word_count"] == 8
        assert row["extracted_text"] == "Hello parsing world! This is a test file."


@pytest.mark.asyncio
async def test_upload_document_invalid_type(
    temp_vault_env: tuple[Path, aiosqlite.Connection], tmp_path: Path
) -> None:
    """Test that upload_document raises UnsupportedFileTypeError for forbidden extensions."""
    vault_dir, db = temp_vault_env
    vault_manager = VaultManager()

    invalid_file = tmp_path / "test.exe"
    invalid_file.write_text("dummy", encoding="utf-8")

    with pytest.raises(UnsupportedFileTypeError):
        await vault_manager.upload_document(invalid_file)
