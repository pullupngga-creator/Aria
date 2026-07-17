use anyhow::{Context, Result};
use rusqlite::Connection;

pub struct PeerSettings {
    pub display_name: String,
    pub listen_port: u16,
    pub trust_mode: String,
}

pub fn get_peer_settings(conn: &Connection) -> Result<PeerSettings> {
    let mut stmt = conn.prepare("SELECT display_name, listen_port, COALESCE(trust_mode, 'manual') FROM settings WHERE id = 1")?;

    let settings = stmt
        .query_row([], |row| {
            Ok(PeerSettings {
                display_name: row.get(0)?,
                listen_port: row.get(1)?,
                trust_mode: row.get(2)?,
            })
        })
        .context("Failed to get settings from database")?;

    Ok(settings)
}
