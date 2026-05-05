import { useCallback, useEffect, useReducer } from "react";
import { listen } from "@tauri-apps/api/event";
import type { Notification, NotifAction } from "../types";

export const MAX_NOTIFICATIONS = 5;

// ── Pure reducer (exported for unit-testing without Tauri) ──────────────────

export function notificationReducer(
  state: Notification[],
  action: NotifAction
): Notification[] {
  switch (action.type) {
    case "ADD": {
      const items =
        state.length >= MAX_NOTIFICATIONS
          ? [...state.slice(1), action.notif]
          : [...state, action.notif];
      return items;
    }
    case "DISMISS":
      return state.filter((n) => n.id !== action.id);
    case "CLEAR_ALL":
      return [];
  }
}

// ── Hook ────────────────────────────────────────────────────────────────────

export function useNotifications() {
  const [notifications, dispatch] = useReducer(notificationReducer, []);

  useEffect(() => {
    let unlisten: (() => void) | undefined;

    listen<Notification>("notification", (event) => {
      dispatch({ type: "ADD", notif: event.payload });
    }).then((fn) => {
      unlisten = fn;
    });

    return () => {
      unlisten?.();
    };
  }, []);

  const dismiss = useCallback((id: string) => {
    dispatch({ type: "DISMISS", id });
  }, []);

  const clearAll = useCallback(() => {
    dispatch({ type: "CLEAR_ALL" });
  }, []);

  return { notifications, dismiss, clearAll };
}
