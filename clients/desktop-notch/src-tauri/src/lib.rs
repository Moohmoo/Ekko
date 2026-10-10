//! Ekko desktop tray popover library module setting up Tauri v2 builder.

pub mod commands;
pub mod ipc;

use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            if let Some(icon) = app.default_window_icon() {
                let _tray = TrayIconBuilder::new()
                    .icon(icon.clone())
                    .tooltip("Ekko - Tampon Cognitif Ambiant")
                    .on_tray_icon_event(|tray, event| {
                        if let TrayIconEvent::Click {
                            button: MouseButton::Left,
                            button_state: MouseButtonState::Up,
                            ..
                        } = event
                        {
                            let app = tray.app_handle();
                            if let Some(window) = app.get_webview_window("main") {
                                if window.is_visible().unwrap_or(false) {
                                    let _ = window.hide();
                                } else {
                                    if let Ok(Some(monitor)) = window.current_monitor() {
                                        let size = monitor.size();
                                        let scale = monitor.scale_factor();
                                        let logical_w = size.width as f64 / scale;
                                        let target_x = (logical_w - 420.0 - 16.0).max(16.0);
                                        let target_y = 36.0;
                                        let _ = window.set_position(tauri::LogicalPosition::new(target_x, target_y));
                                    }
                                    let _ = window.show();
                                    let _ = window.set_focus();
                                }
                            }
                        }
                    })
                    .build(app)?;
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::check_daemon_status,
            commands::submit_prompt_to_daemon,
            commands::get_daemon_notes,
            commands::ingest_file_path,
            commands::ping,
            commands::scan_inbox,
            commands::query_knowledge,
            commands::submit_prompt,
            commands::hide_window,
            commands::toggle_window,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Ekko application");
}
