use std::collections::HashMap;
use std::sync::Arc;
use tokio::net::tcp::OwnedWriteHalf;
use tokio::sync::RwLock;

/// Handle to an active peer connection, holding the write-half of the TCP stream.
/// Clone-able because all interior state is wrapped in Arc.
#[derive(Clone)]
pub struct ConnectionHandle {
    pub peer_key: String,
    writer: Arc<tokio::sync::Mutex<OwnedWriteHalf>>,
}

impl ConnectionHandle {
    pub fn new(peer_key: String, writer: OwnedWriteHalf) -> Self {
        Self {
            peer_key,
            writer: Arc::new(tokio::sync::Mutex::new(writer)),
        }
    }

    /// Send a length-prefixed raw message to this peer.
    ///
    /// Framing: [u32 big-endian byte length][payload bytes]
    /// Per RULES.md §4 — length-prefixed framing prevents stream desynchronization.
    pub async fn send_raw(&self, payload: &[u8]) -> anyhow::Result<()> {
        use tokio::io::AsyncWriteExt;
        let mut writer = self.writer.lock().await;
        let len = payload.len() as u32;
        writer.write_all(&len.to_be_bytes()).await?;
        writer.write_all(payload).await?;
        writer.flush().await?;
        Ok(())
    }
}

/// Thread-safe registry of all active peer TCP connections.
/// Keyed by peer fingerprint (or temporary IP string before handshake).
#[derive(Clone, Default)]
pub struct ConnectionManager {
    connections: Arc<RwLock<HashMap<String, ConnectionHandle>>>,
}

impl ConnectionManager {
    pub fn new() -> Self {
        Self {
            connections: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Register a new connection for a peer (replaces any existing entry).
    pub async fn insert(&self, key: String, handle: ConnectionHandle) {
        self.connections.write().await.insert(key, handle);
    }

    /// Re-key an existing connection (used during handshake when temp IP
    /// key is replaced with the verified peer fingerprint).
    pub async fn rekey(&self, old_key: &str, new_key: String) {
        let mut map = self.connections.write().await;
        if let Some(handle) = map.remove(old_key) {
            map.insert(new_key, handle);
        }
    }

    /// Remove a connection (called on disconnect or error).
    pub async fn remove(&self, key: &str) -> Option<ConnectionHandle> {
        self.connections.write().await.remove(key)
    }

    /// Check if a peer has an active connection.
    pub async fn is_connected(&self, key: &str) -> bool {
        self.connections.read().await.contains_key(key)
    }

    /// Get a cloned handle to send a message.
    pub async fn get(&self, key: &str) -> Option<ConnectionHandle> {
        self.connections.read().await.get(key).cloned()
    }

    /// Return the keys (fingerprints or temp IPs) of all connected peers.
    pub async fn connected_peers(&self) -> Vec<String> {
        self.connections.read().await.keys().cloned().collect()
    }
}
