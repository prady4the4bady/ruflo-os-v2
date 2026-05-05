import { describe, it, expect } from "vitest";
import {
  notificationReducer,
  MAX_NOTIFICATIONS,
} from "../src/hooks/useNotifications";
import type { Notification } from "../src/types";

function makeNotif(id: string, duration = 4_000): Notification {
  return { id, title: `Title ${id}`, body: `Body ${id}`, icon: null, duration_ms: duration };
}

describe("notificationReducer – ADD", () => {
  it("adds a notification to an empty queue", () => {
    const result = notificationReducer([], { type: "ADD", notif: makeNotif("a") });
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe("a");
  });

  it("accumulates notifications up to MAX_NOTIFICATIONS", () => {
    let state: Notification[] = [];
    for (let i = 0; i < MAX_NOTIFICATIONS; i++) {
      state = notificationReducer(state, { type: "ADD", notif: makeNotif(`n${i}`) });
    }
    expect(state).toHaveLength(MAX_NOTIFICATIONS);
  });

  it("drops the oldest when the queue is full", () => {
    let state: Notification[] = [];
    for (let i = 0; i <= MAX_NOTIFICATIONS; i++) {
      state = notificationReducer(state, { type: "ADD", notif: makeNotif(`n${i}`) });
    }
    expect(state).toHaveLength(MAX_NOTIFICATIONS);
    // n0 should have been evicted
    expect(state.find((n) => n.id === "n0")).toBeUndefined();
    // n1 through n5 should remain
    expect(state[0].id).toBe("n1");
    expect(state[MAX_NOTIFICATIONS - 1].id).toBe(`n${MAX_NOTIFICATIONS}`);
  });
});

describe("notificationReducer – DISMISS", () => {
  it("removes a notification by id", () => {
    const initial = [makeNotif("x"), makeNotif("y"), makeNotif("z")];
    const result = notificationReducer(initial, { type: "DISMISS", id: "y" });
    expect(result).toHaveLength(2);
    expect(result.find((n) => n.id === "y")).toBeUndefined();
  });

  it("is a no-op when the id does not exist", () => {
    const initial = [makeNotif("a")];
    const result = notificationReducer(initial, { type: "DISMISS", id: "nonexistent" });
    expect(result).toHaveLength(1);
  });
});

describe("notificationReducer – CLEAR_ALL", () => {
  it("empties the queue", () => {
    const initial = [makeNotif("a"), makeNotif("b"), makeNotif("c")];
    const result = notificationReducer(initial, { type: "CLEAR_ALL" });
    expect(result).toHaveLength(0);
  });

  it("is safe on an empty queue", () => {
    const result = notificationReducer([], { type: "CLEAR_ALL" });
    expect(result).toHaveLength(0);
  });
});

describe("MAX_NOTIFICATIONS constant", () => {
  it("is exactly 5", () => {
    expect(MAX_NOTIFICATIONS).toBe(5);
  });
});
