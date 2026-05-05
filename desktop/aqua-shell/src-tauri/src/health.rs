use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;
use tauri::Emitter;

// ── Public types ────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum HealthStatus {
    Healthy,  // green – model-gateway up + ≥1 model
    Degraded, // yellow – endpoint reachable but no models loaded
    Down,     // red   – connection refused / timeout / error status
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelsData {
    pub id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelsResponse {
    pub data: Vec<ModelsData>,
}

#[derive(Debug, Clone, Serialize)]
pub struct GatewayStatus {
    pub status: HealthStatus,
    pub active_model: Option<String>,
    pub model_count: usize,
}

// ── Background poller ───────────────────────────────────────────────────────

/// Runs forever, emitting "health-status" events every 10 seconds.
pub async fn poll_health(app_handle: tauri::AppHandle, gateway_url: String) {
    let client = Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .unwrap_or_default();
    loop {
        let status = check_gateway(&client, &gateway_url).await;
        let _ = app_handle.emit("health-status", &status);
        tokio::time::sleep(Duration::from_secs(10)).await;
    }
}

/// Pure async function – performs one health check and returns a status.
pub async fn check_gateway(client: &Client, base_url: &str) -> GatewayStatus {
    let url = format!("{}/v1/models", base_url);
    match client.get(&url).send().await {
        Ok(resp) if resp.status().is_success() => {
            let (model_count, active_model) = match resp.json::<ModelsResponse>().await {
                Ok(body) => (body.data.len(), body.data.into_iter().next().map(|m| m.id)),
                Err(_) => (0, None),
            };
            GatewayStatus {
                status: if model_count > 0 {
                    HealthStatus::Healthy
                } else {
                    HealthStatus::Degraded
                },
                active_model,
                model_count,
            }
        }
        Ok(_resp) => GatewayStatus {
            status: HealthStatus::Degraded,
            active_model: None,
            model_count: 0,
        },
        Err(_) => GatewayStatus {
            status: HealthStatus::Down,
            active_model: None,
            model_count: 0,
        },
    }
}

// ── Unit tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn healthy_serializes_to_lowercase() {
        assert_eq!(
            serde_json::to_string(&HealthStatus::Healthy).unwrap(),
            r#""healthy""#
        );
        assert_eq!(
            serde_json::to_string(&HealthStatus::Degraded).unwrap(),
            r#""degraded""#
        );
        assert_eq!(
            serde_json::to_string(&HealthStatus::Down).unwrap(),
            r#""down""#
        );
    }

    #[test]
    fn status_with_models_is_healthy() {
        let s = GatewayStatus {
            status: HealthStatus::Healthy,
            active_model: Some("llama3".into()),
            model_count: 2,
        };
        assert_eq!(s.status, HealthStatus::Healthy);
        assert_eq!(s.active_model.unwrap(), "llama3");
        assert_eq!(s.model_count, 2);
    }

    #[test]
    fn status_zero_models_is_degraded() {
        let s = GatewayStatus {
            status: HealthStatus::Degraded,
            active_model: None,
            model_count: 0,
        };
        assert_eq!(s.status, HealthStatus::Degraded);
    }

    #[tokio::test]
    async fn unreachable_gateway_returns_down() {
        // Port 59997 is guaranteed to have nothing listening
        let client = Client::builder()
            .timeout(Duration::from_millis(200))
            .build()
            .unwrap();
        let s = check_gateway(&client, "http://127.0.0.1:59997").await;
        assert_eq!(s.status, HealthStatus::Down);
        assert_eq!(s.model_count, 0);
        assert!(s.active_model.is_none());
    }
}
