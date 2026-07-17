pub mod connection_manager;
pub mod discovery;
pub mod heartbeat;
pub mod monitor;
pub mod tcp_server;

use std::time::Duration;
use tauri::Emitter;
use tokio::io::AsyncWriteExt;
use tokio::net::TcpStream;

/// Internal function to connect to a peer by fingerprint.
/// Can be called from both Tauri commands and from mDNS discovery listener.
pub async fn connect_to_peer_internal(
    state: &tauri::State<'_, crate::AppState>,
    app: &tauri::AppHandle,
    fingerprint: &str,
) -> Result<(), String> {
    let conn_mgr = &state.connection_manager;

    // Already connected? Return early — idempotent.
    if conn_mgr.is_connected(fingerprint).await {
        return Ok(());
    }

    // Lookup peer address from DB
    let (ip, port) = {
        let conn = state.db.lock().map_err(|e| e.to_string())?;
        let peers = crate::db::peers::list_peers(&conn).map_err(|e| e.to_string())?;
        let peer = peers
            .into_iter()
            .find(|p| p.fingerprint == fingerprint)
            .ok_or_else(|| format!("Peer '{}' not found in database", fingerprint))?;
        let ip = peer
            .ip_address
            .ok_or_else(|| "Peer has no known IP address".to_string())?;
        let port = peer.port as u16;
        (ip, port)
    };

    let addr = format!("{}:{}", ip, port);

    // Connect with timeout
    let stream = tokio::time::timeout(
        std::time::Duration::from_secs(5),
        tokio::net::TcpStream::connect(&addr),
    )
    .await
    .map_err(|_| format!("Connection to {} timed out", addr))?
    .map_err(|e| format!("Failed to connect to {}: {}", addr, e))?;

    let (reader, writer) = stream.into_split();
    let handle =
        crate::network::connection_manager::ConnectionHandle::new(fingerprint.to_string(), writer);
    conn_mgr.insert(fingerprint.to_string(), handle).await;

    // Notify frontend immediately
    let _ = app.emit(
        "peer:connected",
        serde_json::json!({
            "fingerprint": fingerprint,
            "direction": "outbound"
        }),
    );

    // Spawn persistent read loop for this outbound stream
    let fp_clone = fingerprint.to_string();
    let app_clone = app.clone();
    let mgr_clone = conn_mgr.clone();
    tokio::spawn(async move {
        crate::network::tcp_server::run_read_loop(
            reader,
            fp_clone.clone(),
            app_clone.clone(),
            mgr_clone.clone(),
        )
        .await;

        // Cleanup when loop exits
        mgr_clone.remove(&fp_clone).await;
        let _ = app_clone.emit(
            "peer:disconnected",
            serde_json::json!({ "fingerprint": fp_clone }),
        );
        println!("[TCP] Outbound connection to {} closed", fp_clone);
    });

    Ok(())
}

#[tauri::command]
#[specta::specta]
pub fn start_discovery(
    state: tauri::State<'_, crate::AppState>,
    app: tauri::AppHandle,
) -> Result<String, String> {
    let mut daemon_lock = state.mdns_daemon.lock().map_err(|e| e.to_string())?;
    if daemon_lock.is_some() {
        return Ok("Discovery is already running.".to_string());
    }

    let conn = state.db.lock().map_err(|e| e.to_string())?;
    let settings = crate::db::settings::get_peer_settings(&conn).map_err(|e| e.to_string())?;

    let daemon = crate::network::discovery::start_mdns_broadcast(
        &state.identity.public_key_hex,
        &state.identity.fingerprint,
        &settings.display_name,
        settings.listen_port,
    )
    .map_err(|e| e.to_string())?;

    let (heartbeat_state, heartbeat_rx) = crate::network::heartbeat::HeartbeatState::new();

    // Store heartbeat sender in app state
    *state.heartbeat_sender.lock().map_err(|e| e.to_string())? = Some(heartbeat_state.sender());

    crate::network::discovery::start_mdns_listener(
        app.clone(),
        daemon.clone(),
        state.identity.fingerprint.clone(),
        heartbeat_state.clone(),
    );

    // Start heartbeat monitor
    crate::network::heartbeat::start_heartbeat_monitor(app.clone(), heartbeat_state, heartbeat_rx);

    *daemon_lock = Some(daemon);

    Ok("mDNS Discovery started successfully!".to_string())
}

/// Manually connect to a peer by IP address and port.
/// Used as fallback when mDNS is unavailable.
#[tauri::command]
#[specta::specta]
pub async fn connect_manual(
    state: tauri::State<'_, crate::AppState>,
    app: tauri::AppHandle,
    ip: String,
    port: u16,
) -> Result<crate::db::peers::PeerRow, String> {
    let addr = format!("{}:{}", ip, port);

    // Attempt TCP connection with timeout
    let stream = TcpStream::connect(&addr)
        .await
        .map_err(|_| format!("Could not connect to {}", addr))?;

    // Perform a simple handshake: send our fingerprint, expect theirs
    let our_fingerprint = &state.identity.fingerprint;
    let handshake_msg = serde_json::json!({
        "type": "handshake",
        "fingerprint": our_fingerprint,
        "version": 1
    });

    // Write handshake
    let (mut reader, mut writer) = stream.into_split();
    let msg_bytes = serde_json::to_vec(&handshake_msg).map_err(|e| e.to_string())?;
    let len = msg_bytes.len() as u32;
    writer
        .write_all(&len.to_be_bytes())
        .await
        .map_err(|e| e.to_string())?;
    writer
        .write_all(&msg_bytes)
        .await
        .map_err(|e| e.to_string())?;

    // Read response with timeout
    let their_handshake = tokio::time::timeout(Duration::from_secs(5), async {
        use tokio::io::AsyncReadExt;
        let mut len_buf = [0u8; 4];
        reader.read_exact(&mut len_buf).await?;
        let msg_len = u32::from_be_bytes(len_buf) as usize;
        let mut buf = vec![0u8; msg_len];
        reader.read_exact(&mut buf).await?;
        let payload: serde_json::Value = serde_json::from_slice(&buf)?;
        Ok::<_, anyhow::Error>(payload)
    })
    .await
    .map_err(|_| "Handshake timed out".to_string())?
    .map_err(|e: anyhow::Error| e.to_string())?;

    let their_fingerprint = their_handshake["fingerprint"]
        .as_str()
        .ok_or("Peer did not provide fingerprint".to_string())?
        .to_string();

    let their_name = their_handshake["display_name"]
        .as_str()
        .map(|s| s.to_string());

    // Upsert peer in database
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    let public_key = their_fingerprint.clone(); // In manual connect, public_key = fingerprint (simplified)

    // Determine network interface from IP
    let network_interface = ip.split('.').take(3).collect::<Vec<_>>().join(".");

    crate::db::peers::upsert_peer(
        &conn,
        &public_key,
        &their_fingerprint,
        their_name.as_deref(),
        None, // hostname unknown from manual connect
        Some(&ip),
        port,
        Some(&network_interface),
    )
    .map_err(|e| e.to_string())?;

    // Get the full PeerRow
    let peers = crate::db::peers::list_peers(&conn).map_err(|e| e.to_string())?;
    let peer_row = peers
        .into_iter()
        .find(|p| p.fingerprint == their_fingerprint)
        .ok_or("Failed to find newly connected peer".to_string())?;

    // Emit discovery event
    let _ = app.emit(
        "peer:discovered",
        crate::network::discovery::PeerDiscoveredPayload {
            fingerprint: their_fingerprint,
            display_name: their_name,
            is_online: true,
            ip_address: Some(ip),
            hostname: None,
        },
    );

    // Notify heartbeat
    if let Some(sender) = state
        .heartbeat_sender
        .lock()
        .map_err(|e| e.to_string())?
        .as_ref()
    {
        let _ = sender.send(crate::network::heartbeat::HeartbeatAction::Seen(
            peer_row.fingerprint.clone(),
        ));
    }

    Ok(peer_row)
}
