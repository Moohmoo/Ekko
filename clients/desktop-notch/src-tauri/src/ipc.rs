//! UNIX socket IPC client connecting Tauri desktop notch to Ekko Python core.

use serde_json::{json, Value};
use std::path::Path;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixStream;

pub const DEFAULT_SOCKET_PATH: &str = "/tmp/ekko.sock";

/// Send a JSON-RPC 2.0 request and return the result value.
pub async fn send_jsonrpc_request(
    method: &str,
    params: Value,
) -> Result<Value, String> {
    println!("[IPC Rust -> Python] {} : {}", method, params);

    if !Path::new(DEFAULT_SOCKET_PATH).exists() {
        return Err(format!("Socket Unix introuvable sur {}", DEFAULT_SOCKET_PATH));
    }

    let stream = UnixStream::connect(DEFAULT_SOCKET_PATH)
        .await
        .map_err(|e| format!("Impossible de se connecter au socket daemon: {}", e))?;

    let (reader, mut writer) = stream.into_split();
    let mut reader = BufReader::new(reader);

    let payload = json!({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    });

    let mut line_out = payload.to_string();
    line_out.push('\n');

    writer
        .write_all(line_out.as_bytes())
        .await
        .map_err(|e| format!("Échec d'écriture dans le socket: {}", e))?;
    writer
        .flush()
        .await
        .map_err(|e| format!("Échec de flush du socket: {}", e))?;

    let mut line_in = String::new();
    reader
        .read_line(&mut line_in)
        .await
        .map_err(|e| format!("Échec de lecture de la réponse socket: {}", e))?;

    println!("[IPC Python -> Rust] {} : {}", method, line_in.trim());

    let response: Value = serde_json::from_str(&line_in)
        .map_err(|e| format!("Réponse JSON invalide du daemon: {}", e))?;

    if let Some(err) = response.get("error") {
        return Err(format!("Erreur JSON-RPC: {}", err));
    }

    Ok(response.get("result").cloned().unwrap_or(Value::Null))
}

/// Backwards compatibility alias for call_rpc.
pub async fn call_rpc(
    _socket_path: &str,
    method: &str,
    params: Value,
) -> Result<Value, String> {
    send_jsonrpc_request(method, params).await
}

/// Stream EngineEvents from submit_prompt to an asynchronous consumer callback.
pub async fn stream_prompt<F>(
    _socket_path: &str,
    prompt: &str,
    session_id: &str,
    mut on_event: F,
) -> Result<(), String>
where
    F: FnMut(Value) -> Result<(), String> + Send,
{
    println!("[IPC Rust -> Python] submit_prompt : prompt='{}', session='{}'", prompt, session_id);

    if !Path::new(DEFAULT_SOCKET_PATH).exists() {
        return Err(format!("Socket Unix introuvable sur {}", DEFAULT_SOCKET_PATH));
    }

    let stream = UnixStream::connect(DEFAULT_SOCKET_PATH)
        .await
        .map_err(|e| format!("Impossible de se connecter au socket daemon: {}", e))?;

    let (reader, mut writer) = stream.into_split();
    let mut reader = BufReader::new(reader);

    let payload = json!({
        "jsonrpc": "2.0",
        "method": "submit_prompt",
        "params": {
            "prompt": prompt,
            "session_id": session_id
        },
        "id": 1
    });

    let mut line_out = payload.to_string();
    line_out.push('\n');

    writer
        .write_all(line_out.as_bytes())
        .await
        .map_err(|e| format!("Échec d'écriture dans le socket: {}", e))?;
    writer
        .flush()
        .await
        .map_err(|e| format!("Échec de flush du socket: {}", e))?;

    let mut line_in = String::new();
    loop {
        line_in.clear();
        let bytes_read = reader
            .read_line(&mut line_in)
            .await
            .map_err(|e| format!("Échec de lecture du flux socket: {}", e))?;

        if bytes_read == 0 {
            break;
        }

        println!("[IPC Stream Line] {}", line_in.trim());

        if let Ok(event) = serde_json::from_str::<Value>(&line_in) {
            let is_completed = {
                let event_type = event
                    .get("type")
                    .or_else(|| event.get("event"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                matches!(
                    event_type,
                    "turn_completed" | "TurnCompleted" | "engine_error" | "EngineError"
                )
            };

            on_event(event)?;

            if is_completed {
                break;
            }
        }
    }

    Ok(())
}
