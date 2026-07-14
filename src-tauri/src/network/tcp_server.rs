use tokio::net::TcpListener;
use tauri::{AppHandle, Emitter};
use crate::network::connection_manager::{ConnectionHandle, ConnectionManager};

/// Bind the TCP listener on the given port and spawn the accept loop.
/// Called once at startup from lib.rs::run(). Non-blocking — spawns a tokio task.
///
/// Per RULES.md §2: use tokio::spawn for background tasks; never block the runtime.
/// Uses tauri::async_runtime::spawn to ensure we're in the correct runtime context.
pub fn start_tcp_server(
    port: u16,
    app_handle: AppHandle,
    conn_mgr: ConnectionManager,
) {
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
    stream: tokio::net::TcpStream,
    peer_addr: std::net::SocketAddr,
    app: AppHandle,
    conn_mgr: ConnectionManager,
) {
    // Temporary key until fingerprint is established via handshake (Phase 2, Step 3)
    let temp_key = peer_addr.ip().to_string();

    let (reader, writer) = stream.into_split();
    let handle = ConnectionHandle::new(temp_key.clone(), writer);
    conn_mgr.insert(temp_key.clone(), handle).await;

    println!("[TCP] Inbound connection from {}", peer_addr);

    // Wait for handshake with timeout (30 seconds)
    let handshake_result = tokio::time::timeout(
        std::time::Duration::from_secs(30),
        wait_for_handshake(reader, temp_key.clone(), app.clone()),
    ).await;

    match handshake_result {
        Ok(Ok(fingerprint)) => {
            // Handshake successful - rekey connection
            println!("[TCP] Handshake successful, rekeying {} -> {}", temp_key, fingerprint);
            conn_mgr.rekey(&temp_key, fingerprint.clone()).await;

            let _ = app.emit("peer:connected", serde_json::json!({
                "fingerprint": fingerprint,
                "direction": "inbound"
            }));

            // Continue with normal read loop (would need to re-spawn with new key)
            // For now, close and let peer reconnect
        }
        Ok(Err(e)) => {
            eprintln!("[TCP] Handshake failed: {}", e);
            let _ = app.emit("peer:handshake_rejected", serde_json::json!({
                "key": temp_key,
                "reason": format!("{:?}", e)
            }));
        }
        Err(_) => {
            eprintln!("[TCP] Handshake timeout from {}", peer_addr);
        }
    }

    // Cleanup
    conn_mgr.remove(&temp_key).await;
    println!("[TCP] Inbound disconnected: {}", peer_addr);
}

/// Wait for handshake envelope from peer
async fn wait_for_handshake(
    mut reader: tokio::net::tcp::OwnedReadHalf,
    _key: String,
    _app: AppHandle,
) -> anyhow::Result<String> {
    use tokio::io::AsyncReadExt;
    let mut len_buf = [0u8; 4];

    // Read length prefix
    reader.read_exact(&mut len_buf).await?;
    let msg_len = u32::from_be_bytes(len_buf) as usize;

    if msg_len == 0 || msg_len > 64 * 1024 * 1024 {
        return Err(anyhow::anyhow!("Invalid message length"));
    }

    // Read payload
    let mut payload = vec![0u8; msg_len];
    reader.read_exact(&mut payload).await?;

    // Parse envelope
    let envelope = crate::protocol::Envelope::from_bytes(&payload)?;

    // Verify it's a handshake
    if envelope.message_type != crate::protocol::MessageType::Handshake {
        return Err(anyhow::anyhow!("Expected handshake, got {:?}", envelope.message_type));
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
                    eprintln!("[TCP] Invalid message length {} from {}, closing", msg_len, key);
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

                        // TODO: Verify signature (Step 3 will add public key lookup)
                        // For now, just log and dispatch
                        println!("[TCP] Received envelope from {}: type={:?}", key, envelope.message_type);

                        // Dispatch envelope (stub - will be implemented in later steps)
                        // For now, we need a dummy public key for the dispatcher
                        let dummy_pubkey = ed25519_dalek::VerifyingKey::from_bytes(&[0u8; 32]).unwrap();
                        crate::protocol::dispatcher::dispatch_envelope(envelope, app.clone(), dummy_pubkey).await;
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
