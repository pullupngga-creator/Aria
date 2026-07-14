use tokio::time::{interval, Duration};
use std::sync::Arc;
use tokio::sync::Mutex;
use tauri::{AppHandle, Emitter, Manager};
use crate::db::peers;

/// Tracks the current network interface state
#[derive(Debug, Clone)]
pub struct NetworkState {
    inner: Arc<Mutex<NetworkInner>>,
}

#[derive(Debug, Clone)]
struct NetworkInner {
    /// Last known IP addresses (one per interface)
    last_ips: Vec<String>,
    /// Whether mDNS is working
    mdns_degraded: bool,
}

#[derive(serde::Serialize, Clone)]
pub struct NetworkChangedPayload {
    pub ips: Vec<String>,
    pub changed: bool,
    pub mdns_degraded: bool,
}

impl NetworkState {
    pub fn new() -> Self {
        Self {
            inner: Arc::new(Mutex::new(NetworkInner {
                last_ips: Vec::new(),
                mdns_degraded: false,
            })),
        }
    }

    /// Returns current IP addresses
    pub async fn get_ips(&self) -> Vec<String> {
        self.inner.lock().await.last_ips.clone()
    }

    /// Reports whether mDNS is degraded
    pub async fn is_mdns_degraded(&self) -> bool {
        self.inner.lock().await.mdns_degraded
    }

    /// Set mDNS degradation status
    pub async fn set_mdns_degraded(&self, degraded: bool) {
        self.inner.lock().await.mdns_degraded = degraded;
    }

    /// Force a manual IP refresh and return whether it changed
    pub async fn refresh_ips(&self) -> bool {
        let new_ips = get_local_ips();
        let mut inner = self.inner.lock().await;
        let changed = inner.last_ips != new_ips;
        inner.last_ips = new_ips;
        changed
    }
}

/// Gets all local IP addresses (IPv4 only, non-loopback)
fn get_local_ips() -> Vec<String> {
    local_ip_address::list_afinet_netifas()
        .unwrap_or_default()
        .into_iter()
        .filter(|(_, ip)| {
            // Filter out loopback and multicast
            !ip.is_loopback()
                && !ip.is_multicast()
                // Filter out link-local addresses (169.254.x.x)
                && !ip.to_string().starts_with("169.254")
        })
        .map(|(_, ip)| ip.to_string())
        .collect()
}

/// Starts the network interface monitor.
///
/// Every 10 seconds, polls all local IP addresses. If any change is detected,
/// emits a `network:changed` event to the frontend with the new IP list.
/// Also clears stale peers and re-broadcasts mDNS on network changes.
pub fn start_network_monitor(
    app_handle: AppHandle,
    network_state: NetworkState,
) {
    tauri::async_runtime::spawn(async move {
        // Initial population
        let initial_ips = get_local_ips();
        {
            let mut inner = network_state.inner.lock().await;
            inner.last_ips = initial_ips;
        }

        let mut tick = interval(Duration::from_secs(10));

        loop {
            tick.tick().await;

            let new_ips = get_local_ips();
            let mut inner = network_state.inner.lock().await;
            let changed = inner.last_ips != new_ips;

            if changed {
                // Store the old IPs for comparison (for future use)
                let _old_ips = inner.last_ips.clone();
                inner.last_ips = new_ips.clone();
                let is_degraded = inner.mdns_degraded;

                // Clear stale peers from old network
                if let Ok(conn) = crate::db::get_connection() {
                    let _ = peers::clear_stale_peers(&conn, &new_ips);
                }

                // Re-broadcast mDNS on the new network
                if let Some(daemon) = app_handle.state::<crate::AppState>()
                    .mdns_daemon.lock().unwrap().as_ref() {
                    // Get display name from settings
                    let display_name = if let Ok(conn) = crate::db::get_connection() {
                        crate::db::settings::get_peer_settings(&conn)
                            .map(|s| s.display_name)
                            .unwrap_or_else(|_| "Aria User".to_string())
                    } else {
                        "Aria User".to_string()
                    };
                    
                    let _ = crate::network::discovery::rebroadcast_mdns(
                        daemon,
                        &app_handle.state::<crate::AppState>().identity.public_key_hex,
                        &app_handle.state::<crate::AppState>().identity.fingerprint,
                        &display_name,
                        9473, // Will be updated from settings in a future iteration
                    );
                }

                // Emit network change event
                let _ = app_handle.emit("network:changed", NetworkChangedPayload {
                    ips: new_ips.clone(),
                    changed: true,
                    mdns_degraded: is_degraded,
                });
            }
        }
    });
}