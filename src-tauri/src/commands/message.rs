use crate::protocol::message::MessagePayload;
use crate::protocol::{Envelope, MessageType};
use tauri::{AppHandle, Emitter};

/// Send a text message to a peer
#[tauri::command]
#[specta::specta]
pub async fn send_message(
    state: tauri::State<'_, crate::AppState>,
    app: AppHandle,
    fingerprint: String,
    content: String,
    reply_to: Option<String>,
) -> Result<String, String> {
    let conn_mgr = state.connection_manager.clone();
    let identity = state.identity.clone();

    // Check if connected
    if !conn_mgr.is_connected(&fingerprint).await {
        return Err("Not connected to peer".to_string());
    }

    // Create message payload
    let payload = MessagePayload::new(content, reply_to.clone());
    let message_id = payload.message_id.clone();

    // Store in DB as pending
    {
        let db_guard = state.db.lock().map_err(|e| e.to_string())?;
        crate::db::messages::store_message(
            &db_guard,
            &message_id,
            &fingerprint,
            "sent",
            &payload.content,
            payload.timestamp,
            reply_to.as_deref(),
            "pending",
        )
        .map_err(|e| e.to_string())?;
    }

    // Wrap in envelope
    let envelope = Envelope::new(
        MessageType::Message,
        identity.fingerprint.clone(),
        serde_json::to_value(payload).unwrap(),
        &identity,
    );
    let envelope_bytes = envelope.to_bytes().map_err(|e| e.to_string())?;

    // Send via connection handle
    let handle = conn_mgr
        .get(&fingerprint)
        .await
        .ok_or_else(|| "Connection handle not found".to_string())?;

    handle
        .send_raw(&envelope_bytes)
        .await
        .map_err(|e| e.to_string())?;

    // Emit event
    let _ = app.emit(
        "message:sent",
        serde_json::json!({
            "message_id": message_id,
            "fingerprint": fingerprint,
            "content": envelope.payload.get("content").and_then(|v| v.as_str()).unwrap_or(""),
            "timestamp": envelope.timestamp,
        }),
    );

    println!("[Message] Sent message {} to {}", message_id, fingerprint);
    Ok(message_id)
}

/// Get message history for a peer
#[tauri::command]
#[specta::specta]
pub fn get_messages(
    state: tauri::State<'_, crate::AppState>,
    fingerprint: String,
) -> Result<Vec<crate::db::messages::MessageRow>, String> {
    let db_guard = state.db.lock().map_err(|e| e.to_string())?;
    crate::db::messages::get_messages(&db_guard, &fingerprint).map_err(|e| e.to_string())
}
