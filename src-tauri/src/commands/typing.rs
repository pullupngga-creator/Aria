use crate::protocol::{Envelope, MessageType};
use crate::protocol::message::TypingPayload;
use tauri::{AppHandle, Manager};
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, specta::Type)]
pub struct SendTypingArgs {
    pub fingerprint: String,
    pub is_typing: bool,
}

/// Send typing indicator to a peer
#[tauri::command]
#[specta::specta]
pub async fn send_typing(
    args: SendTypingArgs,
    app: AppHandle,
) -> Result<(), String> {
    let app_state = app.state::<crate::AppState>();
    let identity = &app_state.identity;
    
    // Create typing payload
    let typing_payload = TypingPayload::new(args.is_typing);
    let payload = serde_json::to_value(typing_payload)
        .map_err(|e| format!("Failed to serialize typing payload: {}", e))?;
    
    // Create envelope
    let envelope = Envelope::new(
        MessageType::Typing,
        identity.fingerprint.clone(),
        payload,
        identity,
    );
    
    // Serialize envelope
    let envelope_bytes = envelope.to_bytes()
        .map_err(|e| format!("Failed to serialize envelope: {}", e))?;
    
    // Send via connection manager
    let conn_mgr = &app_state.connection_manager;
    let handle = conn_mgr.get(&args.fingerprint).await
        .ok_or_else(|| format!("No connection to peer: {}", args.fingerprint))?;
    
    handle.send_raw(&envelope_bytes)
        .await
        .map_err(|e| format!("Failed to send typing indicator: {}", e))?;
    
    println!("[Typing] Sent typing indicator to {}: is_typing={}", args.fingerprint, args.is_typing);
    Ok(())
}
