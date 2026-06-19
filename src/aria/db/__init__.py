"""Database package for Aria — public entry-point."""

import logging

from aria.db.connection import db_path, get_async_connection, get_connection
from aria.db.migrations import init_schema

logger = logging.getLogger(__name__)

__all__ = ["init_db", "get_connection", "get_async_connection"]


def init_db() -> None:
    """Initialize the Aria database on first launch.

    Creates ``~/.local/share/aria/aria.db`` (XDG-compliant path),
    applies the full schema DDL, and seeds ``app_settings`` defaults.
    Idempotent — safe to call on every application startup.
    """
    with get_connection() as conn:
        init_schema(conn)
    logger.info("Database initialized at %s", db_path())
