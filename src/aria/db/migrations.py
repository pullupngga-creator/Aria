"""SQLite DDL migrations for Aria — idempotent, safe to run on every launch."""

import sqlite3

# Default key/value rows for app_settings (INSERT OR IGNORE → re-run safe)
_SETTINGS_DEFAULTS: list[tuple[str, str]] = [
    ("theme", '"dark"'),
    ("default_provider", '"gemini"'),
    ("default_model", '"gemini-1.5-pro"'),
    ("gemini_api_key", '""'),
    ("claude_api_key", '""'),
    ("max_context_sources", "5"),
    ("auto_save_interval", "30"),
    ("vault_panel_width", "320"),
]

_DDL = """
-- ── documents ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id              TEXT    PRIMARY KEY,
    filename        TEXT    NOT NULL,
    original_path   TEXT    NOT NULL,
    storage_path    TEXT    NOT NULL,
    file_type       TEXT    NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    word_count      INTEGER NOT NULL DEFAULT 0,
    token_count     INTEGER NOT NULL DEFAULT 0,
    extracted_text  TEXT,
    is_active       INTEGER NOT NULL DEFAULT 0,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_active
    ON documents(is_active);

CREATE INDEX IF NOT EXISTS idx_documents_filename
    ON documents(filename);

-- FTS5 virtual table for full-text vault search
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts
    USING fts5(
        filename,
        extracted_text,
        content='documents',
        content_rowid='rowid'
    );

-- ── conversations ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conversations (
    id             TEXT     PRIMARY KEY,
    title          TEXT     NOT NULL DEFAULT 'New Chat',
    model_provider TEXT     NOT NULL,
    model_name     TEXT     NOT NULL,
    system_prompt  TEXT,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_archived    INTEGER  NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_conversations_updated
    ON conversations(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversations_archived
    ON conversations(is_archived);

-- ── messages ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id              TEXT     PRIMARY KEY,
    conversation_id TEXT     NOT NULL
        REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT     NOT NULL
        CHECK(role IN ('user', 'assistant', 'system')),
    content         TEXT     NOT NULL,
    sources_used    TEXT,
    token_count     INTEGER  NOT NULL DEFAULT 0,
    model_provider  TEXT,
    model_name      TEXT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages(conversation_id, created_at DESC);

-- ── app_settings ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS app_settings (
    key        TEXT     PRIMARY KEY,
    value      TEXT     NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def init_schema(conn: sqlite3.Connection) -> None:
    """Create all tables, indexes, and FTS virtual table if they don't exist.

    Idempotent — safe to call on every application startup.
    """
    conn.executescript(_DDL)

    # Seed default settings (INSERT OR IGNORE keeps existing user values intact)
    conn.executemany(
        "INSERT OR IGNORE INTO app_settings(key, value) VALUES (?, ?)",
        _SETTINGS_DEFAULTS,
    )
    conn.commit()
