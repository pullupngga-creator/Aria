use crate::db::messages;
use crate::db::peers;
use crate::protocol::handshake::HandshakePayload;
use crate::protocol::message::{MessagePayload, ReceiptPayload, TypingPayload};
use crate::protocol::{Envelope, MessageType};
use ed25519_dalek::VerifyingKey;
use tauri::{AppHandle, Emitter, Manager};

/// Dispatch an envelope to the appropriate handler based on message type.
/// At this step, most handlers are stubs that just log. They will be implemented in later steps.
pub async fn dispatch_envelope(
    envelope: Envelope,
    app: AppHandle,
    sender_public_key: Option<VerifyingKey>,
) {
    // Verify signature if we have the sender's public key
    if let Some(pubkey) = sender_public_key {
        if let Err(e) = envelope.verify(&pubkey) {
            eprintln!(
                "[Protocol] Signature verification failed for {}: {}",
                envelope.sender, e
            );
            return;
        }
    } else {
        eprintln!(
            "[Protocol] No public key for {}, skipping signature verification",
            envelope.sender
        );
    }

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
                eprintln!(
                    "[Protocol] Handshake timestamp invalid from {}",
                    handshake.fingerprint
                );
                return;
            }

            // Verify fingerprint matches sender
            if handshake.fingerprint != envelope.sender {
                eprintln!("[Protocol] Handshake fingerprint mismatch");
                return;
            }

            // Check trust status
            let is_blocked = {
                let app_state = app.state::<crate::AppState>();
                let db_guard = app_state.db.lock().unwrap();
                peers::list_peers(&db_guard)
                    .ok()
                    .and_then(|peers| {
                        peers
                            .into_iter()
                            .find(|p| p.fingerprint == handshake.fingerprint)
                    })
                    .map(|p| p.trust_level == "blocked")
                    .unwrap_or(false)
            };

            if is_blocked {
                eprintln!(
                    "[Protocol] Rejecting handshake from blocked peer {}",
                    handshake.fingerprint
                );
                let _ = app.emit(
                    "peer:handshake_rejected",
                    serde_json::json!({
                        "fingerprint": handshake.fingerprint,
                        "reason": "blocked"
                    }),
                );
                return;
            }

            // Rekey connection manager: replace temp IP key with verified fingerprint
            let app_state = app.state::<crate::AppState>();
            app_state
                .connection_manager
                .rekey(&envelope.sender, handshake.fingerprint.clone())
                .await;

            println!(
                "[Protocol] Handshake accepted for {}",
                handshake.fingerprint
            );

            let _ = app.emit(
                "peer:handshake_complete",
                serde_json::json!({
                    "fingerprint": handshake.fingerprint,
                    "display_name": handshake.display_name,
                    "public_key": handshake.public_key
                }),
            );
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
            let _ = app.emit(
                "message:received",
                serde_json::json!({
                    "message_id": message_id,
                    "fingerprint": fingerprint,
                    "content": content,
                    "timestamp": timestamp,
                    "reply_to": reply_to,
                }),
            );

            // Send delivery receipt back to sender
            let receipt = ReceiptPayload::new(message_id.clone(), "delivered".to_string());
            let receipt_envelope = Envelope::new(
                MessageType::Message,
                app.state::<crate::AppState>().identity.fingerprint.clone(),
                serde_json::to_value(receipt).unwrap(),
                &app.state::<crate::AppState>().identity,
            );
            if let Ok(envelope_bytes) = receipt_envelope.to_bytes() {
                if let Some(handle) = app
                    .state::<crate::AppState>()
                    .connection_manager
                    .get(&fingerprint)
                    .await
                {
                    let _ = handle.send_raw(&envelope_bytes).await;
                }
            }
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
            println!(
                "[Protocol] Received typing indicator from {}",
                envelope.sender
            );

            // Parse typing payload
            let typing = match TypingPayload::from_envelope(&envelope) {
                Ok(t) => t,
                Err(e) => {
                    eprintln!("[Protocol] Invalid typing payload: {}", e);
                    return;
                }
            };

            // Emit typing event to frontend
            let _ = app.emit(
                "typing:received",
                serde_json::json!({
                    "fingerprint": envelope.sender,
                    "is_typing": typing.is_typing,
                    "timestamp": typing.timestamp,
                }),
            );
        }
    }
}
