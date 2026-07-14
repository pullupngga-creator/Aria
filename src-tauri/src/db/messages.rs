use rusqlite::{params, Connection};
use anyhow::{Context, Result};
use serde::Serialize;
use specta::Type;

#[derive(Debug, Serialize, Type, Clone)]
pub struct MessageRow {
    pub id: i32,
    pub message_id: String,
    pub peer_fingerprint: String,
    pub direction: String, // "sent" or "received"
    pub content: String,
    pub timestamp: i32, // Changed from i64 to i32 for Specta compatibility
    pub reply_to: Option<String>,
    pub status: String, // "pending", "delivered", "read", "failed"
}

/// Create messages table
pub fn init_schema(conn: &Connection) -> Result<()> {
    conn.execute(
        "CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE NOT NULL,
            peer_fingerprint TEXT NOT NULL,
            direction TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            reply_to TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (peer_fingerprint) REFERENCES peers(fingerprint)
        )",
        [],
    ).context("Failed to create messages table")?;

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_peer ON messages(peer_fingerprint)",
        [],
    ).context("Failed to create peer index")?;

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)",
        [],
    ).context("Failed to create timestamp index")?;

    Ok(())
}

/// Store a new message in the database
pub fn store_message(
    conn: &Connection,
    message_id: &str,
    peer_fingerprint: &str,
    direction: &str,
    content: &str,
    timestamp: i32,
    reply_to: Option<&str>,
    status: &str,
) -> Result<()> {
    conn.execute(
        "INSERT INTO messages (message_id, peer_fingerprint, direction, content, timestamp, reply_to, status)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
        params![message_id, peer_fingerprint, direction, content, timestamp, reply_to, status],
    ).context("Failed to store message")?;
    Ok(())
}

/// Update message status
pub fn update_message_status(conn: &Connection, message_id: &str, status: &str) -> Result<()> {
    conn.execute(
        "UPDATE messages SET status = ?1 WHERE message_id = ?2",
        [status, message_id],
    ).context("Failed to update message status")?;
    Ok(())
}

/// Get messages for a peer
pub fn get_messages(conn: &Connection, peer_fingerprint: &str) -> Result<Vec<MessageRow>> {
    let mut stmt = conn.prepare(
        "SELECT id, message_id, peer_fingerprint, direction, content, timestamp, reply_to, status
         FROM messages
         WHERE peer_fingerprint = ?1
         ORDER BY timestamp ASC"
    )?;

    let message_iter = stmt.query_map([peer_fingerprint], |row| {
        Ok(MessageRow {
            id: row.get(0)?,
            message_id: row.get(1)?,
            peer_fingerprint: row.get(2)?,
            direction: row.get(3)?,
            content: row.get(4)?,
            timestamp: row.get(5)?,
            reply_to: row.get(6)?,
            status: row.get(7)?,
        })
    })?;

    let mut messages = Vec::new();
    for msg in message_iter {
        messages.push(msg.context("Failed to read message row")?);
    }

    Ok(messages)
}

/// Get a message by message_id
pub fn get_message_by_id(conn: &Connection, message_id: &str) -> Result<Option<MessageRow>> {
    let mut stmt = conn.prepare(
        "SELECT id, message_id, peer_fingerprint, direction, content, timestamp, reply_to, status
         FROM messages
         WHERE message_id = ?1"
    )?;

    let result = stmt.query_row([message_id], |row| {
        Ok(MessageRow {
            id: row.get(0)?,
            message_id: row.get(1)?,
            peer_fingerprint: row.get(2)?,
            direction: row.get(3)?,
            content: row.get(4)?,
            timestamp: row.get(5)?,
            reply_to: row.get(6)?,
            status: row.get(7)?,
        })
    });

    match result {
        Ok(msg) => Ok(Some(msg)),
        Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
        Err(e) => Err(e.into()),
    }
}
