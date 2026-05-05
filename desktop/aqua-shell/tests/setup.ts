// Global Vitest setup – mock all @tauri-apps/* modules so tests run in Node/jsdom.

import "@testing-library/jest-dom";
import { vi } from "vitest";

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(),
}));

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(() => Promise.resolve(() => {})),
  emit:   vi.fn(),
}));
