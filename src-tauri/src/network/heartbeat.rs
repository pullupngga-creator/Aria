use crate::db::peers;
use std::collections::HashMap;
use std::sync::Arc;
use tauri::{AppHandle, Emitter};
use tokio::sync::mpsc;
use tokio::sync::Mutex;
use tokio::time::{interval, Duration};

/// Tracks heartbeat state for each connected peer
#[derive(Debug, Clone)]
pub struct HeartbeatState {
    /// Map from fingerprint -> (last_seen_timestamp, miss_count)
    peers: Arc<Mutex<HashMap<String, (u64, u32)>>>,
    /// Channel to notify the heartbeat loop about peer changes
    tx: mpsc::UnboundedSender<HeartbeatAction>,
}

#[derive(Debug, Clone)]
pub enum HeartbeatAction {
    /// A peer was just seen (ping/pong received, or mDNS resolution)
    Seen(String),
    /// A peer is no longer connected (connection closed)
    Remove(String),
}

impl HeartbeatState {
    pub fn new() -> (Self, mpsc::UnboundedReceiver<HeartbeatAction>) {
        let (tx, rx) = mpsc::unbounded_channel();
        let state = Self {
            peers: Arc::new(Mutex::new(HashMap::new())),
            tx,
        };
        (state, rx)
    }

    /// Report that a peer was just seen (resets its miss counter)
    pub async fn seen(&self, fingerprint: &str) {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        let mut map = self.peers.lock().await;
        map.insert(fingerprint.to_string(), (now, 0));
    }

    pub fn sender(&self) -> mpsc::UnboundedSender<HeartbeatAction> {
        self.tx.clone()
    }
}

/// Spawns the heartbeat monitoring loop.
///
/// Every 30 seconds, checks all tracked peers. If a peer has missed 3 consecutive
/// pings (90 seconds), it's marked offline and a `peer:offline` event is emitted.
///
/// Also listens for `HeartbeatAction` messages to add/remove peers from tracking.
pub fn start_heartbeat_monitor(
    app_handle: AppHandle,
    state: HeartbeatState,
    mut action_rx: mpsc::UnboundedReceiver<HeartbeatAction>,
) {
    tauri::async_runtime::spawn(async move {
        let mut tick = interval(Duration::from_secs(30));
        let timeout_misses: u32 = 3; // 90 seconds without a ping

        loop {
            tokio::select! {
                _ = tick.tick() => {
                    let now = std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap_or_default()
                        .as_secs();
                    let mut map = state.peers.lock().await;
                    let mut stale_peers = Vec::new();

                    for (fingerprint, (last_seen, misses)) in map.iter_mut() {
                        if now - *last_seen > 30 {
                            *misses += 1;
                            if *misses >= timeout_misses {
                                stale_peers.push(fingerprint.clone());
                            }
                        }
                    }

                    for fp in stale_peers {
                        map.remove(&fp);
                        // Update DB
                        if let Ok(conn) = crate::db::get_connection() {
                            let _ = peers::set_peer_offline(&conn, &fp);
                        }
                        // Emit event
                        let _ = app_handle.emit("peer:offline", crate::network::discovery::PeerDiscoveredPayload {
                            fingerprint: fp.clone(),
                            display_name: None,
                            is_online: false,
                            ip_address: None,
                            hostname: None,
                        });
                    }
                }
                Some(action) = action_rx.recv() => {
                    match action {
                        HeartbeatAction::Seen(fp) => {
                            let now = std::time::SystemTime::now()
                                .duration_since(std::time::UNIX_EPOCH)
                                .unwrap_or_default()
                                .as_secs();
                            let mut map = state.peers.lock().await;
                            map.insert(fp, (now, 0));
                        }
                        HeartbeatAction::Remove(fp) => {
                            let mut map = state.peers.lock().await;
                            map.remove(&fp);
                        }
                    }
                }
            }
        }
    });
}
