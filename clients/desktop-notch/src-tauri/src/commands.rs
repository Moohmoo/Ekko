//! Tauri frontend commands bridging the webview to the Ekko IPC server.

use crate::ipc::{self, DEFAULT_SOCKET_PATH};
use serde_json::{json, Value};
use tauri::{AppHandle, Emitter, Manager};

#[tauri::command]
pub async fn check_daemon_status() -> Result<bool, String> {
    match ipc::send_jsonrpc_request("ping", json!({})).await {
        Ok(res) => {
            let is_ok = res.get("status").and_then(|s| s.as_str()) == Some("ok");
            Ok(is_ok)
        }
        Err(_) => Ok(false),
    }
}

#[tauri::command]
pub async fn ping() -> Result<Value, String> {
    ipc::send_jsonrpc_request("ping", json!({})).await
}

#[tauri::command]
pub async fn submit_prompt_to_daemon(
    prompt: String,
    session_id: Option<String>,
    app: AppHandle,
) -> Result<String, String> {
    let session = session_id.unwrap_or_else(|| "desktop_popover".to_string());
    let mut accumulated_tokens = String::new();

    ipc::stream_prompt(DEFAULT_SOCKET_PATH, &prompt, &session, |event| {
        if let Some(delta) = event.get("delta").and_then(|v| v.as_str()) {
            accumulated_tokens.push_str(delta);
        }
        let _ = app.emit("engine-event", event);
        Ok(())
    })
    .await?;

    if accumulated_tokens.trim().is_empty() {
        Ok("Réponse reçue du daemon sans contenu texte additionnel.".to_string())
    } else {
        Ok(accumulated_tokens)
    }
}

#[tauri::command]
pub async fn get_daemon_notes(limit: Option<u32>) -> Result<Vec<Value>, String> {
    let params = json!({
        "limit": limit.unwrap_or(20)
    });
    let result = ipc::send_jsonrpc_request("scan_inbox", params).await?;
    match result {
        Value::Array(arr) => Ok(arr),
        _ => Ok(vec![]),
    }
}

#[tauri::command]
pub async fn ingest_file_path(
    path: String,
    app: AppHandle,
) -> Result<Value, String> {
    let prompt = format!("Analyse, résume et sauvegarde dans mes notes le document suivant : {}", path);
    let session = "desktop_ingest".to_string();

    ipc::stream_prompt(DEFAULT_SOCKET_PATH, &prompt, &session, |event| {
        let _ = app.emit("engine-event", event);
        Ok(())
    })
    .await?;

    Ok(json!({
        "status": "ingested",
        "path": path
    }))
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
    ipc::send_jsonrpc_request("scan_inbox", params).await
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
    ipc::send_jsonrpc_request("query_knowledge", params).await
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
            if let Ok(Some(monitor)) = window.current_monitor() {
                let size = monitor.size();
                let scale_factor = monitor.scale_factor();
                let logical_w = size.width as f64 / scale_factor;
                let target_x = (logical_w - 420.0 - 16.0).max(16.0);
                let target_y = 36.0;
                let _ = window.set_position(tauri::LogicalPosition::new(target_x, target_y));
            }
            window
                .show()
                .map_err(|e| format!("Failed to show window: {}", e))?;
            let _ = window.set_focus();
        }
    }
    Ok(())
}
