use tauri::State;

use crate::dock::{get_launch_command, DockApp};
use crate::health::{check_gateway, GatewayStatus};
use crate::notify::{Notification, Queue};
use crate::tasks::submit_task;

// ── Health ──────────────────────────────────────────────────────────────────

/// One-shot health check against model-gateway (also called by the background
/// poller; exposed here so the frontend can request a manual refresh).
#[tauri::command]
pub async fn get_health_status() -> Result<GatewayStatus, String> {
    let url = std::env::var("MODEL_GATEWAY_URL")
        .unwrap_or_else(|_| "http://localhost:11430".to_string());
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .map_err(|e| e.to_string())?;
    Ok(check_gateway(&client, &url).await)
}

// ── Notifications ───────────────────────────────────────────────────────────

#[tauri::command]
pub async fn get_notifications(queue: State<'_, Queue>) -> Result<Vec<Notification>, String> {
    let q = queue.lock().await;
    Ok(q.clone())
}

#[tauri::command]
pub async fn dismiss_notification(id: String, queue: State<'_, Queue>) -> Result<(), String> {
    let mut q = queue.lock().await;
    q.retain(|n| n.id != id);
    Ok(())
}

// ── Dock ────────────────────────────────────────────────────────────────────

/// Launch a dock application via `sh -c "<fallback-chain>"`.
/// Uses `std::process::Command` so the child is fully detached from Tauri.
#[tauri::command]
pub fn launch_dock_app(app: DockApp) -> Result<(), String> {
    let cmd = get_launch_command(&app);
    std::process::Command::new(&cmd[0])
        .args(&cmd[1..])
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn()
        .map(|_| ())
        .map_err(|e| e.to_string())
}

// ── Wallpaper ───────────────────────────────────────────────────────────────

/// Reads `~/.prady/wallpaper` which should contain a file path.
/// Returns `None` (null in JS) when the file doesn't exist or HOME is unset.
#[tauri::command]
pub async fn get_wallpaper() -> Option<String> {
    let home = std::env::var("HOME").ok()?;
    let path = format!("{home}/.prady/wallpaper");
    tokio::fs::read_to_string(&path)
        .await
        .ok()
        .map(|s| s.trim().to_string())
}

// ── Tasks ───────────────────────────────────────────────────────────────────

/// POST a natural-language goal to workflow-engine and return its task ID.
#[tauri::command]
pub async fn submit_task_cmd(goal: String) -> Result<String, String> {
    let url = std::env::var("WORKFLOW_ENGINE_URL")
        .unwrap_or_else(|_| "http://localhost:8001".to_string());
    let resp = submit_task(&url, &goal).await?;
    Ok(resp.task_id_resolved())
}
