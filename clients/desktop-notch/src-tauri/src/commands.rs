//! Tauri frontend commands bridging the webview to the Ekko IPC server.

use crate::ipc::{self, DEFAULT_SOCKET_PATH};
use serde_json::{json, Value};
use tauri::{AppHandle, Emitter, Manager};

#[tauri::command]
pub async fn ping() -> Result<Value, String> {
    ipc::call_rpc(DEFAULT_SOCKET_PATH, "ping", json!({})).await
}

#[tauri::command]
pub async fn scan_inbox(
    status: Option<String>,
    source_id: Option<String>,
    limit: Option<u32>,
) -> Result<Value, String> {
    let params = json!({
        "status": status,
        "source_id": source_id,
        "limit": limit.unwrap_or(10),
    });
    ipc::call_rpc(DEFAULT_SOCKET_PATH, "scan_inbox", params).await
}

#[tauri::command]
pub async fn query_knowledge(
    query: String,
    mode: Option<String>,
    limit: Option<u32>,
) -> Result<Value, String> {
    let params = json!({
        "query": query,
        "mode": mode.unwrap_or_else(|| "hybrid".to_string()),
        "limit": limit.unwrap_or(5),
    });
    ipc::call_rpc(DEFAULT_SOCKET_PATH, "query_knowledge", params).await
}

#[tauri::command]
pub async fn submit_prompt(
    prompt: String,
    session_id: Option<String>,
    app: AppHandle,
) -> Result<(), String> {
    let session = session_id.unwrap_or_else(|| "notch_default".to_string());
    ipc::stream_prompt(DEFAULT_SOCKET_PATH, &prompt, &session, |event| {
        app.emit("engine-event", event)
            .map_err(|e| format!("Failed to emit event: {}", e))
    })
    .await
}

#[tauri::command]
pub async fn hide_window(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        window
            .hide()
            .map_err(|e| format!("Failed to hide window: {}", e))?;
    }
    Ok(())
}

#[tauri::command]
pub async fn toggle_window(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        if window.is_visible().unwrap_or(false) {
            window
                .hide()
                .map_err(|e| format!("Failed to hide window: {}", e))?;
        } else {
            window
                .show()
                .map_err(|e| format!("Failed to show window: {}", e))?;
            let _ = window.set_focus();
        }
    }
    Ok(())
}

