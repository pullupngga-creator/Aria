use crate::network::connection_manager::{ConnectionHandle, ConnectionManager};
use hex;
use tauri::{AppHandle, Emitter, Manager};
use tokio::net::TcpListener;

/// Bind the TCP listener on the given port and spawn the accept loop.
/// Called once at startup from lib.rs::run(). Non-blocking — spawns a tokio task.
///
/// Per RULES.md §2: use tokio::spawn for background tasks; never block the runtime.
/// Uses tauri::async_runtime::spawn to ensure we're in the correct runtime context.
pub fn start_tcp_server(port: u16, app_handle: AppHandle, conn_mgr: ConnectionManager) {
    tauri::async_runtime::spawn(async move {
        let addr = format!("0.0.0.0:{}", port);
        let listener = match TcpListener::bind(&addr).await {
            Ok(l) => {
                println!("[TCP] Listening on {}", addr);
                l
            }
            Err(e) => {
                eprintln!("[TCP] Failed to bind on {}: {}", addr, e);
                return;
            }
        };

        loop {
            match listener.accept().await {
                Ok((stream, peer_addr)) => {
                    let app = app_handle.clone();
                    let mgr = conn_mgr.clone();
                    // Spawn a separate task per inbound connection — RULES.md §2
                    tokio::spawn(handle_inbound(stream, peer_addr, app, mgr));
                }
                Err(e) => {
                    eprintln!("[TCP] Accept error: {}", e);
                    // Small back-off to avoid spinning on persistent errors
                    tokio::time::sleep(std::time::Duration::from_millis(100)).await;
                }
            }
        }
    });
}

/// Handle an inbound TCP stream from an unknown remote peer.
/// At this step the peer is stored under a temporary IP-based key.
/// Step 3 (handshake) will call `conn_mgr.rekey()` to replace it with a fingerprint.
async fn handle_inbound(
    mut stream: tokio::net::TcpStream,
    peer_addr: std::net::SocketAddr,
    app: AppHandle,
    conn_mgr: ConnectionManager,
) {
    // Temporary key until fingerprint is established via handshake (Phase 2, Step 3)
    let temp_key = peer_addr.ip().to_string();

    println!("[TCP] Inbound connection from {}", peer_addr);

    // Wait for handshake with timeout (30 seconds) - work on the whole stream
    let handshake_result = tokio::time::timeout(
        std::time::Duration::from_secs(30),
        wait_for_handshake(&mut stream, temp_key.clone(), app.clone()),
    )
    .await;

    match handshake_result {
        Ok(Ok(fingerprint)) => {
            // Handshake successful - rekey connection
            println!(
                "[TCP] Handshake successful, rekeying {} -> {}",
                temp_key, fingerprint
            );
            conn_mgr.rekey(&temp_key, fingerprint.clone()).await;

            let _ = app.emit(
                "peer:connected",
                serde_json::json!({
                    "fingerprint": fingerprint,
                    "direction": "inbound"
                }),
            );

            // Now split the stream and spawn the read loop for the verified peer
            let (reader, writer) = stream.into_split();
            let handle = ConnectionHandle::new(fingerprint.clone(), writer);
            conn_mgr.insert(fingerprint.clone(), handle).await;

            // Spawn persistent read loop for this inbound stream
            let fp_clone = fingerprint.clone();
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
                println!("[TCP] Inbound connection to {} closed", fp_clone);
            });
        }
        Ok(Err(e)) => {
            eprintln!("[TCP] Handshake failed: {}", e);
            let _ = app.emit(
                "peer:handshake_rejected",
                serde_json::json!({
                    "key": temp_key,
                    "reason": format!("{:?}", e)
                }),
            );
            // Cleanup on handshake failure
            conn_mgr.remove(&temp_key).await;
        }
        Err(_) => {
            eprintln!("[TCP] Handshake timeout from {}", peer_addr);
            // Cleanup on timeout
            conn_mgr.remove(&temp_key).await;
        }
    }
}

/// Wait for handshake envelope from peer (reads from whole stream, not split)
async fn wait_for_handshake(
    stream: &mut tokio::net::TcpStream,
    _key: String,
    _app: AppHandle,
) -> anyhow::Result<String> {
    use tokio::io::AsyncReadExt;
    let mut len_buf = [0u8; 4];

    // Read length prefix
    stream.read_exact(&mut len_buf).await?;
    let msg_len = u32::from_be_bytes(len_buf) as usize;

    if msg_len == 0 || msg_len > 64 * 1024 * 1024 {
        return Err(anyhow::anyhow!("Invalid message length"));
    }

    // Read payload
    let mut payload = vec![0u8; msg_len];
    stream.read_exact(&mut payload).await?;

    // Parse envelope
    let envelope = crate::protocol::Envelope::from_bytes(&payload)?;

    // Verify it's a handshake
    if envelope.message_type != crate::protocol::MessageType::Handshake {
        return Err(anyhow::anyhow!(
            "Expected handshake, got {:?}",
            envelope.message_type
        ));
    }

    // Validate timestamp
    if !envelope.is_timestamp_valid() {
        return Err(anyhow::anyhow!("Invalid timestamp"));
    }

    // Parse handshake payload
    let handshake = crate::protocol::handshake::HandshakePayload::from_envelope(&envelope)?;

    // Verify fingerprint matches
    if handshake.fingerprint != envelope.sender {
        return Err(anyhow::anyhow!("Fingerprint mismatch"));
    }

    // TODO: Verify signature, check trust status
    // For now, just return the fingerprint
    Ok(handshake.fingerprint)
}

/// Drain the read-half of a TCP stream, parse length-prefixed envelopes,
/// verify signatures, and dispatch to handlers.
///
/// Made `pub` so `commands::tcp` can reuse it for outbound connections.
pub async fn run_read_loop(
    mut reader: tokio::net::tcp::OwnedReadHalf,
    key: String,
    app: AppHandle,
    _conn_mgr: ConnectionManager,
) {
    use tokio::io::AsyncReadExt;
    let mut len_buf = [0u8; 4];

    loop {
        // Read 4-byte length prefix
        match reader.read_exact(&mut len_buf).await {
            Ok(_) => {
                let msg_len = u32::from_be_bytes(len_buf) as usize;

                // Guard against malformed/huge payloads
                if msg_len == 0 || msg_len > 64 * 1024 * 1024 {
                    eprintln!(
                        "[TCP] Invalid message length {} from {}, closing",
                        msg_len, key
                    );
                    break;
                }

                // Read payload
                let mut payload = vec![0u8; msg_len];
                if let Err(e) = reader.read_exact(&mut payload).await {
                    eprintln!("[TCP] Failed to read payload from {}: {}", key, e);
                    break;
                }

                // Parse envelope
                match crate::protocol::Envelope::from_bytes(&payload) {
                    Ok(envelope) => {
                        // Validate timestamp
                        if !envelope.is_timestamp_valid() {
                            eprintln!("[TCP] Invalid timestamp from {}, rejecting", key);
                            continue;
                        }

                        // Look up peer's public key for signature verification
                        let peer_pubkey = {
                            let state = app.state::<crate::AppState>();
                            let db = state.db.lock().ok();
                            db.and_then(|conn| {
                                crate::db::peers::get_peer_public_key(&conn, &envelope.sender)
                                    .ok()
                                    .flatten()
                            })
                        };

                        let pubkey = match peer_pubkey {
                            Some(hex) => {
                                let bytes = match hex::decode(&hex) {
                                    Ok(b) => b,
                                    Err(_) => continue,
                                };
                                let arr: [u8; 32] = match bytes.try_into() {
                                    Ok(a) => a,
                                    Err(_) => continue,
                                };
                                match ed25519_dalek::VerifyingKey::from_bytes(&arr) {
                                    Ok(pk) => Some(pk),
                                    Err(_) => continue,
                                }
                            }
                            None => None,
                        };

                        // If we have a public key, verify signature; otherwise skip (unverified peer)
                        if let Some(pubkey) = pubkey {
                            if envelope.verify(&pubkey).is_err() {
                                eprintln!("[TCP] Signature verification failed for {}", key);
                                continue;
                            }
                        } else {
                            eprintln!("[TCP] No public key for {}, skipping verification", key);
                        }

                        println!(
                            "[TCP] Received envelope from {}: type={:?}",
                            key, envelope.message_type
                        );

                        crate::protocol::dispatcher::dispatch_envelope(
                            envelope,
                            app.clone(),
                            pubkey,
                        )
                        .await;
                    }
                    Err(e) => {
                        eprintln!("[TCP] Failed to parse envelope from {}: {}", key, e);
                        // Continue reading - don't close connection on parse error
                    }
                }
            }
            Err(e) if e.kind() == std::io::ErrorKind::UnexpectedEof => {
                // Clean disconnect
                println!("[TCP] Peer {} disconnected (EOF)", key);
                break;
            }
            Err(e) => {
                eprintln!("[TCP] Read error from {}: {}", key, e);
                break;
            }
        }
    }
}
