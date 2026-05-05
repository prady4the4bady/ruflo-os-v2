import { useEffect, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";
import type { GatewayStatus, HealthStatus } from "../types";

const DEFAULT_STATUS: GatewayStatus = {
  status: "down",
  active_model: null,
  model_count: 0,
};

// ── Pure helper – exported for unit testing ─────────────────────────────────

/** Map HTTP status + model count to a HealthStatus string. */
export function deriveStatus(modelCount: number, httpOk: boolean): HealthStatus {
  if (!httpOk) return "down";
  if (modelCount === 0) return "degraded";
  return "healthy";
}

// ── Hook ────────────────────────────────────────────────────────────────────

export function useHealthStatus() {
  const [status, setStatus] = useState<GatewayStatus>(DEFAULT_STATUS);

  useEffect(() => {
    let unlisten: (() => void) | undefined;

    // Subscribe to background-poller events
    listen<GatewayStatus>("health-status", (event) => {
      setStatus(event.payload);
    }).then((fn) => {
      unlisten = fn;
    });

    // Also do an immediate fetch so the UI isn't stale on first render
    invoke<GatewayStatus>("get_health_status")
      .then(setStatus)
      .catch(() => setStatus(DEFAULT_STATUS));

    return () => {
      unlisten?.();
    };
  }, []);

  const refresh = () => {
    invoke<GatewayStatus>("get_health_status")
      .then(setStatus)
      .catch(() => setStatus(DEFAULT_STATUS));
  };

  return { status, refresh };
}
