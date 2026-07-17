use crate::network::connection_manager::ConnectionHandle;
use tauri::{AppHandle, Emitter};

/// Open an outbound TCP connection to a peer and register it in the ConnectionManager.
///
/// Looks up the peer's IP and port from the database by fingerprint.
/// Emits `peer:connected` on success and `peer:disconnected` when the connection drops.
///
/// Per RULES.md §4: 5-second connection timeout, non-blocking I/O via tokio.
#[tauri::command]
#[specta::specta]
pub async fn connect_to_peer(
    state: tauri::State<'_, crate::AppState>,
    app: AppHandle,
    fingerprint: String,
) -> Result<(), String> {
    // Already connected? Return early — idempotent.
    if state.connection_manager.is_connected(&fingerprint).await {
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

    // Connect with timeout — RULES.md §4: implement connection timeouts
    let stream = tokio::time::timeout(
        std::time::Duration::from_secs(5),
        tokio::net::TcpStream::connect(&addr),
    )
    .await
    .map_err(|_| format!("Connection to {} timed out", addr))?
    .map_err(|e| format!("Failed to connect to {}: {}", addr, e))?;

    let (reader, writer) = stream.into_split();
    let handle = ConnectionHandle::new(fingerprint.clone(), writer);
    state
        .connection_manager
        .insert(fingerprint.clone(), handle)
        .await;

    // Notify frontend immediately
    let _ = app.emit(
        "peer:connected",
        serde_json::json!({
            "fingerprint": fingerprint,
            "direction": "outbound"
        }),
    );

    // Spawn persistent read loop for this outbound stream
    let fp_clone = fingerprint.clone();
    let app_clone = app.clone();
    let mgr_clone = state.connection_manager.clone();
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

/// Check whether there is a live TCP connection to the given peer fingerprint.
#[tauri::command]
#[specta::specta]
pub async fn get_connection_status(
    state: tauri::State<'_, crate::AppState>,
    fingerprint: String,
) -> Result<bool, String> {
    Ok(state.connection_manager.is_connected(&fingerprint).await)
}

/// Drop the TCP connection to a peer by removing it from the ConnectionManager.
/// The drop of the OwnedWriteHalf will close the socket.
#[tauri::command]
#[specta::specta]
pub async fn disconnect_peer(
    state: tauri::State<'_, crate::AppState>,
    app: AppHandle,
    fingerprint: String,
) -> Result<(), String> {
    state.connection_manager.remove(&fingerprint).await;
    let _ = app.emit(
        "peer:disconnected",
        serde_json::json!({ "fingerprint": fingerprint }),
    );
    Ok(())
}
