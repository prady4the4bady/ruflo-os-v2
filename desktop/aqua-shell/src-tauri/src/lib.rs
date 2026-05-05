mod commands;
mod dock;
mod health;
mod notify;
mod tasks;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Shared notification queue (Arc<Mutex<Vec<Notification>>>)
    let queue = notify::new_queue();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        // Give one Arc clone to Tauri's state manager so commands can access it
        .manage(queue.clone())
        .setup(move |app| {
            // ── Notification HTTP server on port 11435 ─────────────────────────
            let handle1 = app.handle().clone();
            let q = queue.clone();
            tauri::async_runtime::spawn(async move {
                notify::start_notify_server(q, handle1).await;
            });

            // ── Model-gateway health poller (every 10 s) ───────────────────────
            let handle2 = app.handle().clone();
            let gw_url = std::env::var("MODEL_GATEWAY_URL")
                .unwrap_or_else(|_| "http://localhost:11430".to_string());
            tauri::async_runtime::spawn(async move {
                health::poll_health(handle2, gw_url).await;
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_health_status,
            commands::get_notifications,
            commands::dismiss_notification,
            commands::launch_dock_app,
            commands::get_wallpaper,
            commands::submit_task_cmd,
        ])
        .run(tauri::generate_context!())
        .expect("error while running aqua-shell");
}
