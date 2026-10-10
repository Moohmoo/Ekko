//! Ekko desktop notch library module setting up Tauri v2 builder.

pub mod commands;
pub mod ipc;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            commands::ping,
            commands::scan_inbox,
            commands::query_knowledge,
            commands::submit_prompt,
            commands::set_notch_expanded,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Ekko Desktop Notch application");
}
