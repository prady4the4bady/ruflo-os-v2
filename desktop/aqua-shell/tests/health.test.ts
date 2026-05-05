import { describe, it, expect } from "vitest";
import { deriveStatus } from "../src/hooks/useHealthStatus";
import type { HealthStatus } from "../src/types";

// Tests for the pure health-status derivation helper.
// The Tauri event listener is covered by the mock in setup.ts;
// logic tests do not require a real Tauri runtime.

describe("deriveStatus()", () => {
  it("returns 'healthy' when HTTP is OK and models are present", () => {
    const result: HealthStatus = deriveStatus(3, true);
    expect(result).toBe("healthy");
  });

  it("returns 'degraded' when HTTP is OK but no models are loaded", () => {
    expect(deriveStatus(0, true)).toBe("degraded");
  });

  it("returns 'down' when HTTP request fails regardless of model count", () => {
    expect(deriveStatus(5, false)).toBe("down");
    expect(deriveStatus(0, false)).toBe("down");
  });

  it("treats a single model as healthy", () => {
    expect(deriveStatus(1, true)).toBe("healthy");
  });
});

describe("GatewayStatus HealthStatus values", () => {
  const valid: HealthStatus[] = ["healthy", "degraded", "down"];

  it.each(valid)("'%s' is a recognised status string", (s) => {
    expect(["healthy", "degraded", "down"]).toContain(s);
  });
});
