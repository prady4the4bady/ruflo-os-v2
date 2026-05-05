use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;

// ── Data types ──────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize)]
pub struct TaskPayload {
    pub goal: String,
    pub source: String,
    pub priority: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct TaskResponse {
    /// Some workflow engines return "task_id", others return "id"
    pub task_id: Option<String>,
    pub id: Option<String>,
    pub status: Option<String>,
}

impl TaskResponse {
    pub fn task_id_resolved(&self) -> String {
        self.task_id
            .clone()
            .or_else(|| self.id.clone())
            .unwrap_or_else(|| "unknown".to_string())
    }
}

// ── Pure helpers (testable) ─────────────────────────────────────────────────

pub fn build_task_payload(goal: &str) -> TaskPayload {
    TaskPayload {
        goal: goal.to_string(),
        source: "prady-command-bar".to_string(),
        priority: "normal".to_string(),
    }
}

// ── HTTP call ───────────────────────────────────────────────────────────────

pub async fn submit_task(engine_url: &str, goal: &str) -> Result<TaskResponse, String> {
    let client = Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| e.to_string())?;

    let payload = build_task_payload(goal);
    let url = format!("{}/tasks", engine_url);

    let resp = client
        .post(&url)
        .json(&payload)
        .send()
        .await
        .map_err(|e| format!("request failed: {e}"))?;

    if !resp.status().is_success() {
        return Err(format!("workflow-engine returned HTTP {}", resp.status()));
    }

    resp.json::<TaskResponse>()
        .await
        .map_err(|e| format!("failed to parse response: {e}"))
}

// ── Unit tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn payload_sets_all_fields() {
        let p = build_task_payload("Open Firefox and navigate to github.com");
        assert_eq!(p.goal, "Open Firefox and navigate to github.com");
        assert_eq!(p.source, "prady-command-bar");
        assert_eq!(p.priority, "normal");
    }

    #[test]
    fn payload_accepts_empty_goal() {
        let p = build_task_payload("");
        assert_eq!(p.goal, "");
        assert_eq!(p.source, "prady-command-bar");
    }

    #[test]
    fn payload_serializes_to_json() {
        let p = build_task_payload("test goal");
        let json = serde_json::to_value(&p).unwrap();
        assert_eq!(json["goal"], "test goal");
        assert_eq!(json["source"], "prady-command-bar");
        assert_eq!(json["priority"], "normal");
    }

    #[test]
    fn task_response_resolves_task_id_field() {
        let r = TaskResponse {
            task_id: Some("abc-123".into()),
            id: None,
            status: Some("queued".into()),
        };
        assert_eq!(r.task_id_resolved(), "abc-123");
    }

    #[test]
    fn task_response_falls_back_to_id_field() {
        let r = TaskResponse {
            task_id: None,
            id: Some("xyz-456".into()),
            status: None,
        };
        assert_eq!(r.task_id_resolved(), "xyz-456");
    }

    #[test]
    fn task_response_unknown_when_both_none() {
        let r = TaskResponse {
            task_id: None,
            id: None,
            status: None,
        };
        assert_eq!(r.task_id_resolved(), "unknown");
    }

    #[tokio::test]
    async fn submit_task_returns_err_when_unreachable() {
        let result = submit_task("http://127.0.0.1:59996", "test goal").await;
        assert!(result.is_err());
        assert!(
            result.unwrap_err().contains("request failed"),
            "error message should say 'request failed'"
        );
    }
}
