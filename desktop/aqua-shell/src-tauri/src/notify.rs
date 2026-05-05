use axum::{extract::State, routing::post, Json, Router};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tauri::Emitter;
use tokio::sync::Mutex;
use uuid::Uuid;

// ── Constants ───────────────────────────────────────────────────────────────

pub const MAX_QUEUE: usize = 5;

// ── Data types ──────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NotifyRequest {
    pub title: String,
    pub body: String,
    pub icon: Option<String>,
    pub duration_ms: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Notification {
    pub id: String,
    pub title: String,
    pub body: String,
    pub icon: Option<String>,
    pub duration_ms: u64,
}

pub type Queue = Arc<Mutex<Vec<Notification>>>;

// ── Pure helpers (testable without Tauri) ───────────────────────────────────

pub fn new_queue() -> Queue {
    Arc::new(Mutex::new(Vec::new()))
}

/// Build a `Notification` from an incoming request, assigning a UUID.
pub fn build_notification(req: NotifyRequest) -> Notification {
    Notification {
        id: Uuid::new_v4().to_string(),
        title: req.title,
        body: req.body,
        icon: req.icon,
        duration_ms: req.duration_ms.unwrap_or(4_000),
    }
}

/// Enqueue `notif`, dropping the oldest entry when the queue is at capacity.
pub fn enqueue(queue: &mut Vec<Notification>, notif: Notification) {
    if queue.len() >= MAX_QUEUE {
        queue.remove(0);
    }
    queue.push(notif);
}

// ── Axum HTTP server ────────────────────────────────────────────────────────

type ServerState = (Queue, tauri::AppHandle);

pub async fn start_notify_server(queue: Queue, app_handle: tauri::AppHandle) {
    let state: ServerState = (queue, app_handle);
    let router = Router::new()
        .route("/notify", post(handle_notify))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind("127.0.0.1:11435")
        .await
        .expect("aqua-shell: failed to bind notification port 11435");

    axum::serve(listener, router)
        .await
        .expect("aqua-shell: notification server crashed");
}

async fn handle_notify(
    State((queue, app_handle)): State<ServerState>,
    Json(req): Json<NotifyRequest>,
) -> Json<serde_json::Value> {
    let notif = build_notification(req);
    {
        let mut q = queue.lock().await;
        enqueue(&mut q, notif.clone());
    }
    let _ = app_handle.emit("notification", &notif);
    Json(serde_json::json!({ "id": notif.id, "queued": true }))
}

// ── Unit tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn make(id: &str) -> Notification {
        Notification {
            id: id.to_string(),
            title: format!("T-{id}"),
            body: format!("B-{id}"),
            icon: None,
            duration_ms: 4_000,
        }
    }

    #[test]
    fn enqueue_up_to_max() {
        let mut q = Vec::new();
        for i in 0..MAX_QUEUE {
            enqueue(&mut q, make(&i.to_string()));
        }
        assert_eq!(q.len(), MAX_QUEUE);
    }

    #[test]
    fn enqueue_drops_oldest_when_full() {
        let mut q = Vec::new();
        // Fill to capacity then add one more
        for i in 0..=MAX_QUEUE {
            enqueue(&mut q, make(&i.to_string()));
        }
        assert_eq!(q.len(), MAX_QUEUE);
        // "0" must have been evicted
        assert_eq!(q[0].id, "1");
        assert_eq!(q[MAX_QUEUE - 1].id, MAX_QUEUE.to_string());
    }

    #[test]
    fn build_notification_defaults_duration_to_4000() {
        let req = NotifyRequest {
            title: "Hello".into(),
            body: "World".into(),
            icon: None,
            duration_ms: None,
        };
        let n = build_notification(req);
        assert_eq!(n.duration_ms, 4_000);
        assert!(!n.id.is_empty(), "UUID must be non-empty");
    }

    #[test]
    fn build_notification_respects_custom_duration_and_icon() {
        let req = NotifyRequest {
            title: "T".into(),
            body: "B".into(),
            icon: Some("bell.png".into()),
            duration_ms: Some(8_000),
        };
        let n = build_notification(req);
        assert_eq!(n.duration_ms, 8_000);
        assert_eq!(n.icon.unwrap(), "bell.png");
    }

    #[tokio::test]
    async fn queue_is_thread_safe_via_arc_mutex() {
        let q = new_queue();
        let q2 = q.clone();
        let handle = tokio::spawn(async move {
            let mut v = q2.lock().await;
            enqueue(&mut v, make("async-item"));
        });
        handle.await.unwrap();
        assert_eq!(q.lock().await.len(), 1);
    }
}
