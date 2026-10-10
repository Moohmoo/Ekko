//! UNIX socket IPC client connecting Tauri desktop notch to Ekko Python core.

use serde_json::{json, Value};
use std::path::Path;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixStream;

pub const DEFAULT_SOCKET_PATH: &str = "/tmp/ekko.sock";

/// Send a JSON-RPC 2.0 request and return the unwrapped result field.
pub async fn call_rpc(
    socket_path: &str,
    method: &str,
    params: Value,
) -> Result<Value, String> {
    if !Path::new(socket_path).exists() {
        return Err(format!("IPC socket not found at {}", socket_path));
    }

    let stream = UnixStream::connect(socket_path)
        .await
        .map_err(|e| format!("Failed to connect to socket: {}", e))?;

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
        .map_err(|e| format!("Failed to write to socket: {}", e))?;
    writer
        .flush()
        .await
        .map_err(|e| format!("Failed to flush socket: {}", e))?;

    let mut line_in = String::new();
    reader
        .read_line(&mut line_in)
        .await
        .map_err(|e| format!("Failed to read socket response: {}", e))?;

    let response: Value = serde_json::from_str(&line_in)
        .map_err(|e| format!("Failed to parse JSON response: {}", e))?;

    if let Some(err) = response.get("error") {
        return Err(format!("RPC Error: {}", err));
    }

    Ok(response.get("result").cloned().unwrap_or(Value::Null))
}

/// Stream EngineEvents from submit_prompt to an asynchronous consumer callback.
pub async fn stream_prompt<F>(
    socket_path: &str,
    prompt: &str,
    session_id: &str,
    mut on_event: F,
) -> Result<(), String>
where
    F: FnMut(Value) -> Result<(), String> + Send,
{
    if !Path::new(socket_path).exists() {
        return Err(format!("IPC socket not found at {}", socket_path));
    }

    let stream = UnixStream::connect(socket_path)
        .await
        .map_err(|e| format!("Failed to connect to socket: {}", e))?;

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
        .map_err(|e| format!("Failed to write to socket: {}", e))?;
    writer
        .flush()
        .await
        .map_err(|e| format!("Failed to flush socket: {}", e))?;

    let mut line_in = String::new();
    loop {
        line_in.clear();
        let bytes_read = reader
            .read_line(&mut line_in)
            .await
            .map_err(|e| format!("Failed reading stream line: {}", e))?;

        if bytes_read == 0 {
            break;
        }

        if let Ok(event) = serde_json::from_str::<Value>(&line_in) {
            let event_type = event
                .get("type")
                .or_else(|| event.get("event"))
                .and_then(|v| v.as_str())
                .unwrap_or("");

            on_event(event)?;

            if matches!(event_type, "turn_completed" | "TurnCompleted" | "engine_error" | "EngineError") {
                break;
            }
        }
    }

    Ok(())
}
