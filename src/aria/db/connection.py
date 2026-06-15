"""SQLite connection factory for Aria."""

import sqlite3
from pathlib import Path

# XDG-compliant data directory — keeps the repo clean at dev time
_DATA_DIR: Path = Path.home() / ".local" / "share" / "aria"
_DB_PATH: Path = _DATA_DIR / "aria.db"


def get_connection() -> sqlite3.Connection:
    """Return an open sqlite3 connection to the Aria database.

    Creates the data directory on first call.
    Connection is configured with:
    - ``row_factory = sqlite3.Row``  (dict-like row access)
    - ``PRAGMA foreign_keys = ON``   (referential integrity)
    - ``PRAGMA journal_mode = WAL``  (safe concurrent reads)
    """
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def db_path() -> Path:
    """Return the resolved path to aria.db (useful for logging)."""
    return _DB_PATH
