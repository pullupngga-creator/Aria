use crate::db::peers;
use anyhow::{Context, Result};
use mdns_sd::{ServiceDaemon, ServiceEvent, ServiceInfo};
use std::collections::HashMap;
use tauri::{AppHandle, Emitter, Manager};

#[derive(serde::Serialize, Clone)]
pub struct PeerDiscoveredPayload {
    pub fingerprint: String,
    pub display_name: Option<String>,
    pub is_online: bool,
    pub ip_address: Option<String>,
    pub hostname: Option<String>,
}

/// Get the primary (non-local) IP address from a list of addresses
/// Prefers IPv4 addresses that are not loopback or link-local
fn get_primary_ip(addresses: &[std::net::IpAddr]) -> Option<String> {
    addresses
        .iter()
        .filter(|ip| {
            !ip.is_loopback() && !ip.is_multicast() && !ip.to_string().starts_with("169.254")
        })
        .filter_map(|ip| {
            // Prefer IPv4 for now (simpler for users)
            if ip.is_ipv4() {
                Some(ip.to_string())
            } else {
                None
            }
        })
        .next()
}

/// Get all valid IP addresses as a comma-separated string
fn get_all_ips_string(addresses: &[std::net::IpAddr]) -> String {
    addresses
        .iter()
        .filter(|ip| {
            !ip.is_loopback() && !ip.is_multicast() && !ip.to_string().starts_with("169.254")
        })
        .map(|ip| ip.to_string())
        .collect::<Vec<_>>()
        .join(",")
}

pub fn start_mdns_broadcast(
    public_key: &str,
    fingerprint: &str,
    display_name: &str,
    listen_port: u16,
) -> Result<ServiceDaemon> {
    let daemon = ServiceDaemon::new().context("Failed to create mDNS daemon")?;

    let service_type = "_aria._tcp.local.";
    let instance_name = format!("{}-{}", display_name, fingerprint);
    let host_name = format!("{}.local.", instance_name);

    let mut properties = HashMap::new();
    properties.insert("id".to_string(), fingerprint.to_string());
    properties.insert("pubkey".to_string(), public_key.to_string());
    properties.insert("name".to_string(), display_name.to_string());
    properties.insert("port".to_string(), listen_port.to_string());

    let service_info = ServiceInfo::new(
        service_type,
        &instance_name,
        &host_name,
        "",
        listen_port,
        Some(properties),
    )
    .context("Failed to create mDNS ServiceInfo")?;

    daemon
        .register(service_info)
        .context("Failed to register mDNS service")?;

    println!(
        "mDNS broadcast started for {} on port {}",
        instance_name, listen_port
    );

    Ok(daemon)
}

pub fn start_mdns_listener(
    app_handle: AppHandle,
    daemon: ServiceDaemon,
    my_fingerprint: String,
    heartbeat_state: crate::network::heartbeat::HeartbeatState,
) {
    println!("[DISCOVERY] Starting mDNS browser for _aria._tcp.local.");
    tauri::async_runtime::spawn(async move {
        let receiver = match daemon.browse("_aria._tcp.local.") {
            Ok(r) => {
                println!("[DISCOVERY] Browser started successfully");
                r
            }
            Err(e) => {
                eprintln!("[DISCOVERY] Failed to browse mDNS: {:#}", e);
                let _ = app_handle.emit(
                    "network:mdns_disabled",
                    serde_json::json!({
                        "error": format!("mDNS discovery failed: {}", e),
                        "degraded": true
                    }),
                );
                return;
            }
        };

        while let Ok(event) = receiver.recv_async().await {
            match event {
                ServiceEvent::ServiceResolved(info) => {
                    let fullname = info.get_fullname();
                    println!("[DISCOVERY] ServiceResolved: {}", fullname);

                    let properties = info.get_properties();
                    let fingerprint = properties.get_property_val_str("id");

                    if let Some(fp) = fingerprint {
                        println!("[DISCOVERY] Parsed fingerprint: {}", fp);

                        if fp == my_fingerprint {
                            println!("[DISCOVERY] Ignoring self: {}", fp);
                            continue;
                        }

                        let display_name = properties
                            .get_property_val_str("name")
                            .map(|s| s.to_string());
                        let public_key = properties
                            .get_property_val_str("pubkey")
                            .unwrap_or(fp)
                            .to_string();

                        // Get all valid IP addresses
                        let all_addresses: Vec<std::net::IpAddr> =
                            info.get_addresses().iter().cloned().collect();
                        let primary_ip = get_primary_ip(&all_addresses);
                        let _all_ips = get_all_ips_string(&all_addresses);

                        let port = info.get_port();
                        let hostname = info.get_hostname().to_string();

                        println!(
                            "[DISCOVERY] Peer details: fp={}, ip={:?}, port={}, hostname={}",
                            fp, primary_ip, port, hostname
                        );

                        {
                            let state = app_handle.state::<crate::AppState>();
                            let conn = state.db.lock().unwrap();

                            // Determine network interface (use primary IP's subnet)
                            let network_interface = primary_ip.as_deref().and_then(|ip| {
                                ip.split('.').take(3).collect::<Vec<_>>().join(".").into()
                            });

                            println!("[DISCOVERY] Upserting peer: {}", fp);
                            if let Err(e) = peers::upsert_peer(
                                &conn,
                                &public_key,
                                fp,
                                display_name.as_deref(),
                                Some(&hostname),
                                primary_ip.as_deref(),
                                port,
                                network_interface.as_deref(),
                            ) {
                                eprintln!("[DISCOVERY] Failed to upsert peer: {:#}", e);
                            }
                        }

                        // Auto-connect to the discovered peer
                        let fp_clone = fp.to_string();
                        let app_handle_clone = app_handle.clone();
                        tokio::spawn(async move {
                            let state = app_handle_clone.state::<crate::AppState>();
                            if let Err(e) = crate::network::connect_to_peer_internal(
                                &state,
                                &app_handle_clone,
                                &fp_clone,
                            )
                            .await
                            {
                                eprintln!(
                                    "[DISCOVERY] Auto-connect failed for {}: {}",
                                    fp_clone, e
                                );
                            }
                        });

                        // Notify heartbeat
                        let _ = heartbeat_state.sender().send(
                            crate::network::heartbeat::HeartbeatAction::Seen(fp.to_string()),
                        );

                        println!("[DISCOVERY] Emitting peer:discovered for {}", fp);
                        let _ = app_handle.emit(
                            "peer:discovered",
                            PeerDiscoveredPayload {
                                fingerprint: fp.to_string(),
                                display_name,
                                is_online: true,
                                ip_address: primary_ip,
                                hostname: Some(hostname),
                            },
                        );
                    }
                }
                ServiceEvent::ServiceRemoved(_, fullname) => {
                    println!("[DISCOVERY] ServiceRemoved: {}", fullname);
                    // fullname format: name-fingerprint._aria._tcp.local.
                    let parts: Vec<&str> = fullname.split("._aria").collect();
                    if let Some(instance_name) = parts.first() {
                        let fp = instance_name.split('-').next_back();
                        if let Some(fingerprint) = fp {
                            if fingerprint == my_fingerprint {
                                continue;
                            }

                            {
                                let state = app_handle.state::<crate::AppState>();
                                let conn = state.db.lock().unwrap();
                                if let Err(e) = peers::set_peer_offline(&conn, fingerprint) {
                                    eprintln!("[DISCOVERY] Failed to set peer offline: {:#}", e);
                                }
                            }

                            let _ = app_handle.emit(
                                "peer:offline",
                                PeerDiscoveredPayload {
                                    fingerprint: fingerprint.to_string(),
                                    display_name: None,
                                    is_online: false,
                                    ip_address: None,
                                    hostname: None,
                                },
                            );
                        }
                    }
                }
                _ => {}
            }
        }

        println!("[DISCOVERY] Browse loop ended - browser stopped");
    });
}

/// Re-broadcast mDNS service with updated information
/// Used when network changes or settings are updated
pub fn rebroadcast_mdns(
    daemon: &ServiceDaemon,
    public_key: &str,
    fingerprint: &str,
    display_name: &str,
    listen_port: u16,
) -> Result<()> {
    let service_type = "_aria._tcp.local.";
    let instance_name = format!("{}-{}", display_name, fingerprint);
    let host_name = format!("{}.local.", instance_name);

    let mut properties = HashMap::new();
    properties.insert("id".to_string(), fingerprint.to_string());
    properties.insert("pubkey".to_string(), public_key.to_string());
    properties.insert("name".to_string(), display_name.to_string());
    properties.insert("port".to_string(), listen_port.to_string());

    let service_info = ServiceInfo::new(
        service_type,
        &instance_name,
        &host_name,
        "",
        listen_port,
        Some(properties),
    )
    .context("Failed to create mDNS ServiceInfo for rebroadcast")?;

    // Unregister old service and register new one
    // Note: mdns-sd doesn't have an unregister method, but we can update by re-registering
    daemon
        .register(service_info)
        .context("Failed to re-register mDNS service")?;

    println!("mDNS rebroadcast completed for {}", instance_name);

    Ok(())
}
