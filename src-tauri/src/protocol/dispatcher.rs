use crate::protocol::{Envelope, MessageType};
use crate::protocol::handshake::HandshakePayload;
use crate::protocol::message::{MessagePayload, TypingPayload};
use crate::db::peers;
use crate::db::messages;
use tauri::{AppHandle, Manager, Emitter};

/// Dispatch an envelope to the appropriate handler based on message type.
/// At this step, most handlers are stubs that just log. They will be implemented in later steps.
pub async fn dispatch_envelope(
    envelope: Envelope,
    app: AppHandle,
    _sender_public_key: ed25519_dalek::VerifyingKey,
) {
    match envelope.message_type {
        MessageType::Handshake => {
            println!("[Protocol] Received handshake from {}", envelope.sender);

            // Parse handshake payload
            let handshake = match HandshakePayload::from_envelope(&envelope) {
                Ok(h) => h,
                Err(e) => {
                    eprintln!("[Protocol] Invalid handshake payload: {}", e);
                    return;
                }
            };

            // Validate handshake timestamp
            if !handshake.is_timestamp_valid() {
                eprintln!("[Protocol] Handshake timestamp invalid from {}", handshake.fingerprint);
                return;
            }

            // Verify fingerprint matches sender
            if handshake.fingerprint != envelope.sender {
                eprintln!("[Protocol] Handshake fingerprint mismatch");
                return;
            }

            // Get peer from DB
            let peer_info = {
                let app_state = app.state::<crate::AppState>();
                let db_guard = app_state.db.lock().unwrap();
                peers::get_peer_public_key(&db_guard, &handshake.fingerprint).ok().flatten()
            };

            // Verify signature using stored public key
            if let Some(stored_pubkey_hex) = peer_info {
                if let Ok(pubkey_bytes) = hex::decode(stored_pubkey_hex) {
                    let pubkey_array: [u8; 32] = pubkey_bytes.try_into().unwrap_or([0u8; 32]);
                    let pubkey = ed25519_dalek::VerifyingKey::from_bytes(&pubkey_array);

                    if let Ok(pubkey) = pubkey {
                        if let Err(e) = envelope.verify(&pubkey) {
                            eprintln!("[Protocol] Handshake signature verification failed: {}", e);
                            return;
                        }
                    }
                }
            }

            // Check trust status
            let is_blocked = {
                let app_state = app.state::<crate::AppState>();
                let db_guard = app_state.db.lock().unwrap();
                peers::list_peers(&db_guard).ok()
                    .and_then(|peers| peers.into_iter().find(|p| p.fingerprint == handshake.fingerprint))
                    .map(|p| p.trust_level == "blocked")
                    .unwrap_or(false)
            };

            if is_blocked {
                eprintln!("[Protocol] Rejecting handshake from blocked peer {}", handshake.fingerprint);
                let _ = app.emit("peer:handshake_rejected", serde_json::json!({
                    "fingerprint": handshake.fingerprint,
                    "reason": "blocked"
                }));
                return;
            }

            // TODO: Rekey connection manager (need access to conn_mgr)
            // This requires passing conn_mgr to dispatcher or using a different approach
            println!("[Protocol] Handshake accepted for {}", handshake.fingerprint);

            let _ = app.emit("peer:handshake_complete", serde_json::json!({
                "fingerprint": handshake.fingerprint,
                "display_name": handshake.display_name,
                "public_key": handshake.public_key
            }));
        }
        MessageType::Message => {
            println!("[Protocol] Received message from {}", envelope.sender);

            // Parse message payload
            let message = match MessagePayload::from_envelope(&envelope) {
                Ok(m) => m,
                Err(e) => {
                    eprintln!("[Protocol] Invalid message payload: {}", e);
                    return;
                }
            };

            // Store in DB as received
            let message_id = message.message_id.clone();
            let fingerprint = envelope.sender.clone();
            let content = message.content.clone();
            let timestamp = message.timestamp;
            let reply_to = message.reply_to.clone();

            {
                let app_state = app.state::<crate::AppState>();
                let db_guard = app_state.db.lock().unwrap();
                let _ = messages::store_message(
                    &db_guard,
                    &message_id,
                    &fingerprint,
                    "received",
                    &content,
                    timestamp,
                    reply_to.as_deref(),
                    "received",
                );
            }

            // Emit event to frontend
            let _ = app.emit("message:received", serde_json::json!({
                "message_id": message_id,
                "fingerprint": fingerprint,
                "content": content,
                "timestamp": timestamp,
                "reply_to": reply_to,
            }));

            // TODO: Send delivery receipt (implement in next iteration)
        }
        MessageType::FileOffer => {
            // Step 5: Implement file transfer
            println!("[Protocol] Received file offer from {}", envelope.sender);
            // TODO: Show file accept UI
        }
        MessageType::FileChunk => {
            // Step 5: Handle file chunk
            println!("[Protocol] Received file chunk from {}", envelope.sender);
        }
        MessageType::FileComplete => {
            // Step 5: Handle file complete
            println!("[Protocol] Received file complete from {}", envelope.sender);
        }
        MessageType::Voice => {
            // Step 6: Handle voice message
            println!("[Protocol] Received voice from {}", envelope.sender);
        }
        MessageType::Heartbeat => {
            // Step 3: Update last_seen timestamp
            println!("[Protocol] Received heartbeat from {}", envelope.sender);
            // TODO: Update peer last_seen in DB
        }
        MessageType::Typing => {
            println!("[Protocol] Received typing indicator from {}", envelope.sender);

            // Parse typing payload
            let typing = match TypingPayload::from_envelope(&envelope) {
                Ok(t) => t,
                Err(e) => {
                    eprintln!("[Protocol] Invalid typing payload: {}", e);
                    return;
                }
            };

            // Emit typing event to frontend
            let _ = app.emit("typing:received", serde_json::json!({
                "fingerprint": envelope.sender,
                "is_typing": typing.is_typing,
                "timestamp": typing.timestamp,
            }));
        }
    }
}
