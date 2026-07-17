use directories::ProjectDirs;
use rusqlite::Connection;
use std::sync::{Arc, Mutex};
use tauri::Manager;
use tauri_specta::{collect_commands, Builder};
use tokio::sync::mpsc;

pub mod commands;
pub mod crypto;
pub mod db;
pub mod network;
pub mod protocol;

pub struct AppState {
    pub db: Mutex<Connection>,
    pub identity: Arc<crypto::Identity>,
    pub mdns_daemon: Mutex<Option<mdns_sd::ServiceDaemon>>,
    pub heartbeat_sender: Mutex<Option<mpsc::UnboundedSender<network::heartbeat::HeartbeatAction>>>,
    pub network_state: network::monitor::NetworkState,
    pub connection_manager: network::connection_manager::ConnectionManager,
}

#[tauri::command]
#[specta::specta]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let builder = Builder::<tauri::Wry>::new().commands(collect_commands![
        greet,
        crypto::get_my_identity,
        network::start_discovery,
        network::connect_manual,
        commands::peers::list_peers,
        commands::peers::trust_peer,
        commands::peers::block_peer,
        commands::peers::untrust_peer,
        commands::tcp::connect_to_peer,
        commands::tcp::get_connection_status,
        commands::tcp::disconnect_peer,
        commands::handshake::send_handshake,
        commands::message::send_message,
        commands::message::get_messages,
        commands::typing::send_typing
    ]);

    #[cfg(debug_assertions)]
    builder
        .export(specta_jsdoc::JSDoc::default(), "../src/bindings.js")
        .expect("Failed to export js bindings");

    #[cfg(debug_assertions)]
    builder
        .export(
            specta_typescript::Typescript::default(),
            "../src/bindings.d.ts",
        )
        .expect("Failed to export ts bindings");

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(builder.invoke_handler())
        .setup(move |app| {
            builder.mount_events(app);

            // Database Initialization
            let proj_dirs = ProjectDirs::from("com", "aria", "aria")
                .expect("Failed to determine project directories");
            let app_data_dir = proj_dirs.data_dir().to_path_buf();

            let conn = db::init(app_data_dir).expect("Failed to initialize database");

            // Crypto Initialization
            let identity = crypto::init().expect("Failed to initialize cryptographic identity");

            let network_state = network::monitor::NetworkState::new();
            let net_state_clone = network_state.clone();
            let connection_manager = network::connection_manager::ConnectionManager::new();
            let conn_mgr_clone = connection_manager.clone();

            app.manage(AppState {
                db: Mutex::new(conn),
                identity,
                mdns_daemon: Mutex::new(None),
                heartbeat_sender: Mutex::new(None),
                network_state,
                connection_manager,
            });

            // Start network interface monitor
            network::monitor::start_network_monitor(app.handle().clone(), net_state_clone);

            // Start TCP server
            let tcp_port = {
                let app_state = app.state::<AppState>();
                let db_guard = app_state.db.lock().unwrap();
                db::settings::get_peer_settings(&db_guard)
                    .map(|s| s.listen_port)
                    .unwrap_or(9473)
            };
            network::tcp_server::start_tcp_server(tcp_port, app.handle().clone(), conn_mgr_clone);

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
