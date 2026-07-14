use crate::protocol::handshake::HandshakePayload;

/// Send our handshake to a connected peer
#[tauri::command]
#[specta::specta]
pub async fn send_handshake(
    state: tauri::State<'_, crate::AppState>,
    _app: tauri::AppHandle,
    fingerprint: String,
) -> Result<(), String> {
    let conn_mgr = state.connection_manager.clone();
    let identity = state.identity.clone();

    // Check if connected
    if !conn_mgr.is_connected(&fingerprint).await {
        return Err("Not connected to peer".to_string());
    }

    // Get our display name
    let display_name = {
        let db_guard = state.db.lock().map_err(|e| e.to_string())?;
        crate::db::settings::get_peer_settings(&db_guard)
            .map(|s| s.display_name)
            .ok()
    };

    // Create handshake payload
    let payload = HandshakePayload::from_identity(
        identity.public_key_hex.clone(),
        identity.fingerprint.clone(),
        display_name,
    );

    // Wrap in envelope
    let envelope = payload.to_envelope(&identity);
    let envelope_bytes = envelope.to_bytes().map_err(|e| e.to_string())?;

    // Send via connection handle
    let handle = conn_mgr.get(&fingerprint).await
        .ok_or_else(|| "Connection handle not found".to_string())?;

    handle.send_raw(&envelope_bytes).await.map_err(|e| e.to_string())?;

    println!("[Handshake] Sent handshake to {}", fingerprint);
    Ok(())
}
