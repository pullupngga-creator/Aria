pub mod messages;
pub mod peers;
pub mod schema;
pub mod settings;
use anyhow::Context;
use rusqlite::Connection;
use std::path::PathBuf;
use std::sync::Mutex;

/// Global database connection for use outside Tauri command context
static DB_CONNECTION: std::sync::OnceLock<Mutex<Connection>> = std::sync::OnceLock::new();

/// Get a reference to the global database connection (for heartbeat/background tasks)
pub fn get_connection() -> Result<std::sync::MutexGuard<'static, Connection>, anyhow::Error> {
    DB_CONNECTION
        .get()
        .ok_or_else(|| anyhow::anyhow!("Database not initialized"))
        .map(|m| m.lock().unwrap())
}

pub fn init(app_data_dir: PathBuf) -> Result<Connection, anyhow::Error> {
    let db_path = app_data_dir.join("aria.db");

    // Ensure the directory exists
    if let Some(parent) = db_path.parent() {
        std::fs::create_dir_all(parent).context("Failed to create application data directory")?;
    }

    let mut conn = Connection::open(&db_path)
        .context(format!("Failed to open SQLite database at {:?}", db_path))?;

    // Read current schema version
    let user_version: i32 = conn
        .query_row("PRAGMA user_version", [], |row| row.get(0))
        .context("Failed to read user_version PRAGMA")?;

    if user_version == 0 {
        // First run - execute full initial schema (fingerprint-based design)
        let tx = conn.transaction().context("Failed to start transaction")?;

        tx.execute_batch(schema::SCHEMA_V1)
            .context("Failed to execute schema batch")?;

        tx.execute_batch("PRAGMA user_version = 1;")
            .context("Failed to update user_version")?;

        tx.commit()
            .context("Failed to commit initial schema transaction")?;

        // Initialize default settings row if it doesn't exist
        conn.execute("INSERT OR IGNORE INTO settings (id) VALUES (1)", [])
            .context("Failed to insert default settings")?;
    } else if user_version == 1 {
        // Migration to V2 - add network_interface column to peers
        let column_exists: bool = conn
            .prepare("PRAGMA table_info(peers)")
            .and_then(|mut stmt| {
                let mut rows = stmt.query([])?;
                while let Some(row) = rows.next()? {
                    if let Ok(name) = row.get::<_, String>(1) {
                        if name == "network_interface" {
                            return Ok(true);
                        }
                    }
                }
                Ok(false)
            })
            .unwrap_or(false);

        if !column_exists {
            conn.execute("ALTER TABLE peers ADD COLUMN network_interface TEXT", [])
                .context("Failed to add network_interface column")?;

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_peers_network ON peers(network_interface)",
                [],
            )
            .context("Failed to create network index")?;
        }

        // Add trust_mode column to settings
        let column_exists: bool = conn
            .prepare("PRAGMA table_info(settings)")
            .and_then(|mut stmt| {
                let mut rows = stmt.query([])?;
                while let Some(row) = rows.next()? {
                    if let Ok(name) = row.get::<_, String>(1) {
                        if name == "trust_mode" {
                            return Ok(true);
                        }
                    }
                }
                Ok(false)
            })
            .unwrap_or(false);

        if !column_exists {
            conn.execute(
                "ALTER TABLE settings ADD COLUMN trust_mode TEXT DEFAULT 'manual'",
                [],
            )
            .context("Failed to add trust_mode column")?;
        }

        conn.execute_batch("PRAGMA user_version = 2;")
            .context("Failed to update user_version to 2")?;
    } else if user_version == 2 {
        // Migration to V3 - add typing_indicators table (if missing)
        let table_exists: bool = conn
            .prepare(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='typing_indicators'",
            )
            .and_then(|mut stmt| {
                let mut rows = stmt.query([])?;
                Ok(rows.next().is_ok())
            })
            .unwrap_or(false);

        if !table_exists {
            conn.execute(
                "CREATE TABLE IF NOT EXISTS typing_indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    peer_id INTEGER NOT NULL REFERENCES peers(id) ON DELETE CASCADE,
                    peer_fingerprint TEXT NOT NULL REFERENCES peers(fingerprint) ON DELETE CASCADE,
                    is_typing BOOLEAN NOT NULL DEFAULT 1,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(peer_fingerprint)
                )",
                [],
            )
            .context("Failed to create typing_indicators table")?;
        }

        conn.execute_batch("PRAGMA user_version = 3;")
            .context("Failed to update user_version to 3")?;
    } else if user_version == 3 {
        // Migration to V4 - add trust_mode column to settings if missing
        let column_exists: bool = conn
            .prepare("PRAGMA table_info(settings)")
            .and_then(|mut stmt| {
                let mut rows = stmt.query([])?;
                while let Some(row) = rows.next()? {
                    if let Ok(name) = row.get::<_, String>(1) {
                        if name == "trust_mode" {
                            return Ok(true);
                        }
                    }
                }
                Ok(false)
            })
            .unwrap_or(false);

        if !column_exists {
            conn.execute(
                "ALTER TABLE settings ADD COLUMN trust_mode TEXT DEFAULT 'manual'",
                [],
            )
            .context("Failed to add trust_mode column")?;
        }

        conn.execute_batch("PRAGMA user_version = 4;")
            .context("Failed to update user_version to 4")?;
    }

    // Enable foreign keys for this connection
    conn.execute_batch("PRAGMA foreign_keys = ON;")
        .context("Failed to enable foreign keys")?;

    // Enable WAL mode for better concurrency (readers don't block writers)
    conn.execute_batch("PRAGMA journal_mode = WAL;")
        .context("Failed to enable WAL mode")?;

    // Set busy timeout to 5 seconds to handle contention gracefully
    conn.execute_batch("PRAGMA busy_timeout = 5000;")
        .context("Failed to set busy timeout")?;

    // Store in global for background tasks
    let _ = DB_CONNECTION.set(Mutex::new({
        let bg_conn = Connection::open(&db_path)
            .context("Failed to open duplicate connection for global access")?;
        bg_conn
            .execute_batch("PRAGMA journal_mode = WAL;")
            .context("Failed to enable WAL mode on background connection")?;
        bg_conn
            .execute_batch("PRAGMA busy_timeout = 5000;")
            .context("Failed to set busy timeout on background connection")?;
        bg_conn
    }));

    Ok(conn)
}
