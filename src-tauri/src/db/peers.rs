use rusqlite::{params, Connection};
use anyhow::{Context, Result};
use serde::Serialize;
use specta::Type;

#[derive(Debug, Serialize, Type, Clone)]
pub struct PeerRow {
    pub id: i32,
    pub fingerprint: String,
    pub display_name: Option<String>,
    pub hostname: Option<String>,
    pub ip_address: Option<String>,
    pub port: u16,
    pub trust_level: String,
    pub is_online: bool,
    pub last_seen: Option<String>,
    pub network_interface: Option<String>,
}

pub fn upsert_peer(
    conn: &Connection,
    public_key: &str,
    fingerprint: &str,
    display_name: Option<&str>,
    hostname: Option<&str>,
    ip_address: Option<&str>,
    port: u16,
    network_interface: Option<&str>,
) -> Result<()> {
    conn.execute(
        "INSERT INTO peers (public_key, fingerprint, display_name, hostname, ip_address, port, is_online, last_seen, network_interface)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, 1, CURRENT_TIMESTAMP, ?7)
         ON CONFLICT(public_key) DO UPDATE SET
            display_name = excluded.display_name,
            hostname = excluded.hostname,
            ip_address = excluded.ip_address,
            port = excluded.port,
            is_online = 1,
            last_seen = CURRENT_TIMESTAMP,
            network_interface = excluded.network_interface;",
        params![public_key, fingerprint, display_name, hostname, ip_address, port, network_interface],
    ).context("Failed to upsert peer")?;
    Ok(())
}

pub fn set_peer_offline(conn: &Connection, fingerprint: &str) -> Result<()> {
    conn.execute(
        "UPDATE peers SET is_online = 0 WHERE fingerprint = ?1",
        params![fingerprint],
    ).context("Failed to set peer offline")?;
    Ok(())
}

pub fn list_peers(conn: &Connection) -> Result<Vec<PeerRow>> {
    let mut stmt = conn.prepare(
        "SELECT id, fingerprint, display_name, hostname, ip_address, port, trust_level, is_online, last_seen, network_interface 
         FROM peers 
         ORDER BY is_online DESC, last_seen DESC"
    ).context("Failed to prepare list_peers query")?;

    let peer_iter = stmt.query_map([], |row| {
        Ok(PeerRow {
            id: row.get(0)?,
            fingerprint: row.get(1)?,
            display_name: row.get(2)?,
            hostname: row.get(3)?,
            ip_address: row.get(4)?,
            port: row.get(5)?,
            trust_level: row.get(6)?,
            is_online: row.get(7)?,
            last_seen: row.get(8)?,
            network_interface: row.get(9)?,
        })
    }).context("Failed to execute list_peers query")?;

    let mut peers = Vec::new();
    for peer in peer_iter {
        peers.push(peer.context("Failed to read peer row")?);
    }
    
    Ok(peers)
}

pub fn set_trust_level(conn: &Connection, fingerprint: &str, level: &str) -> Result<()> {
    conn.execute(
        "UPDATE peers SET trust_level = ?1 WHERE fingerprint = ?2",
        params![level, fingerprint],
    ).context("Failed to set trust level")?;
    Ok(())
}

/// Clear stale peers that were discovered on a different network.
/// When the network changes, peers from the old network should be marked offline.
pub fn clear_stale_peers(conn: &Connection, current_network_ips: &[String]) -> Result<()> {
    // Get all online peers
    let online_peers = list_peers(conn)?;
    
    for peer in online_peers {
        if !peer.is_online {
            continue;
        }
        
        // Check if peer's IP is still on the current network
        // A peer is considered stale if:
        // 1. It has no IP address (edge case)
        // 2. Its IP doesn't match any of the current network IPs
        let is_stale = if let Some(ref peer_ip) = peer.ip_address {
            // Check if the peer IP is in the same subnet as any current IP
            !current_network_ips.iter().any(|current_ip| {
                is_same_subnet(peer_ip, current_ip)
            })
        } else {
            true
        };
        
        if is_stale {
            set_peer_offline(conn, &peer.fingerprint)?;
        }
    }
    
    Ok(())
}

/// Check if two IP addresses are in the same subnet (simple /24 check)
fn is_same_subnet(ip1: &str, ip2: &str) -> bool {
    // Extract first 3 octets for /24 subnet comparison
    let prefix1: String = ip1.split('.').take(3).collect::<Vec<_>>().join(".");
    let prefix2: String = ip2.split('.').take(3).collect::<Vec<_>>().join(".");
    prefix1 == prefix2
}

/// Get a peer's public key by fingerprint
pub fn get_peer_public_key(conn: &Connection, fingerprint: &str) -> Result<Option<String>> {
    let mut stmt = conn.prepare(
        "SELECT public_key FROM peers WHERE fingerprint = ?1"
    )?;
    let mut rows = stmt.query([fingerprint])?;

    if let Some(row) = rows.next()? {
        Ok(Some(row.get(0)?))
    } else {
        Ok(None)
    }
}

/// Update a peer's public key
pub fn update_peer_public_key(conn: &Connection, fingerprint: &str, public_key: &str) -> Result<()> {
    conn.execute(
        "UPDATE peers SET public_key = ?1 WHERE fingerprint = ?2",
        [public_key, fingerprint]
    )?;
    Ok(())
}