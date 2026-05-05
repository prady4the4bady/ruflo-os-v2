// Tauri v2 entry point — delegates to lib::run()
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    aqua_shell_lib::run()
}
