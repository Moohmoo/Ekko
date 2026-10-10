//! Main entry point for Ekko desktop notch binary.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    ekko_desktop_notch_lib::run();
}
