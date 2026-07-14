use crate::db::peers::{self, PeerRow};

#[tauri::command]
#[specta::specta]
pub fn list_peers(state: tauri::State<'_, crate::AppState>) -> Result<Vec<PeerRow>, String> {
    let conn = state.db.lock().map_err(|_| "Failed to lock database".to_string())?;
    peers::list_peers(&conn).map_err(|e| e.to_string())
}

#[tauri::command]
#[specta::specta]
pub fn trust_peer(state: tauri::State<'_, crate::AppState>, fingerprint: String) -> Result<(), String> {
    let conn = state.db.lock().map_err(|_| "Failed to lock database".to_string())?;
    peers::set_trust_level(&conn, &fingerprint, "trusted").map_err(|e| e.to_string())
}

#[tauri::command]
#[specta::specta]
pub fn block_peer(state: tauri::State<'_, crate::AppState>, fingerprint: String) -> Result<(), String> {
    let conn = state.db.lock().map_err(|_| "Failed to lock database".to_string())?;
    peers::set_trust_level(&conn, &fingerprint, "blocked").map_err(|e| e.to_string())
}

#[tauri::command]
#[specta::specta]
pub fn untrust_peer(state: tauri::State<'_, crate::AppState>, fingerprint: String) -> Result<(), String> {
    let conn = state.db.lock().map_err(|_| "Failed to lock database".to_string())?;
    peers::set_trust_level(&conn, &fingerprint, "untrusted").map_err(|e| e.to_string())
}
