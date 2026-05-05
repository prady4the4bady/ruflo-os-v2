from __future__ import annotations

import threading
from typing import Callable

from gi.repository import GLib, Gtk

from prady_shell.services.orchestration import OrchestrationClient


AI_TASK_TITLE = "AI task"


class AITaskBar(Gtk.Box):
    def __init__(
        self,
        client: OrchestrationClient,
        on_notify: Callable[[str, str, str], None],
        on_ai_state: Callable[[str], None],
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class("ai-taskbar")
        self.set_margin_bottom(102)
        self.set_margin_start(18)
        self.set_margin_end(18)
        self.set_margin_top(6)

        self._client = client
        self._on_notify = on_notify
        self._on_ai_state = on_ai_state
        self._task_id: str | None = None
        self._approval_id: str | None = None

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._entry = Gtk.Entry()
        self._entry.set_hexpand(True)
        self._entry.set_placeholder_text("Describe an AI goal, e.g. find all PDFs in Downloads and list them")
        self._entry.connect("activate", lambda *_: self.submit_goal(self._entry.get_text()))

        self._submit = Gtk.Button(label="Run")
        self._submit.connect("clicked", lambda *_: self.submit_goal(self._entry.get_text()))

        self._spinner = Gtk.Spinner()

        row.append(self._entry)
        row.append(self._submit)
        row.append(self._spinner)

        self._status = Gtk.Label(label="Ready")
        self._status.set_xalign(0.0)
        self._status.add_css_class("muted")

        self._approval_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._approval_label = Gtk.Label(label="")
        self._approval_label.set_xalign(0.0)
        self._approval_label.set_hexpand(True)

        approve_btn = Gtk.Button(label="Approve")
        approve_btn.connect("clicked", lambda *_: self._send_approval(True))
        reject_btn = Gtk.Button(label="Reject")
        reject_btn.connect("clicked", lambda *_: self._send_approval(False))

        self._approval_box.append(self._approval_label)
        self._approval_box.append(approve_btn)
        self._approval_box.append(reject_btn)
        self._approval_box.set_visible(False)

        self.set_margin_top(4)
        self.set_margin_bottom(6)
        self.set_margin_start(10)
        self.set_margin_end(10)
        self.append(row)
        self.append(self._status)
        self.append(self._approval_box)

        GLib.timeout_add_seconds(2, self._poll_task)

    def submit_goal(self, goal: str) -> None:
        goal = goal.strip()
        if not goal:
            return

        self._set_busy("thinking", "Submitting task...")

        def worker() -> None:
            try:
                payload = self._client.submit_goal(goal)
                task_id = str(payload.get("task_id") or payload.get("taskId") or "")
                if not task_id:
                    raise RuntimeError("No task_id returned")
                GLib.idle_add(self._task_created, task_id)
            except Exception as exc:
                GLib.idle_add(self._set_error, f"Failed to submit task: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _task_created(self, task_id: str) -> bool:
        self._task_id = task_id
        self._status.set_text(f"Task {task_id[:8]} queued")
        self._on_notify(AI_TASK_TITLE, "Task started", "info")
        self._on_ai_state("executing")
        self._spinner.start()
        return False

    def _set_busy(self, state: str, message: str) -> None:
        self._status.set_text(message)
        self._on_ai_state(state)
        self._spinner.start()

    def _set_error(self, message: str) -> bool:
        self._status.set_text(message)
        self._spinner.stop()
        self._on_ai_state("idle")
        self._on_notify(AI_TASK_TITLE, message, "error")
        return False

    def _poll_task(self) -> bool:
        if not self._task_id:
            return True

        def worker() -> None:
            try:
                task = self._client.get_task(self._task_id or "")
                approvals = self._client.pending_approvals()
                GLib.idle_add(self._on_idle_apply_task_state, task, approvals)
            except Exception:
                return

        threading.Thread(target=worker, daemon=True).start()
        return self._task_id is not None

    def _on_idle_apply_task_state(self, task: dict, approvals: list[dict]) -> bool:
        self._apply_task_state(task, approvals)
        return False

    def _apply_task_state(self, task: dict, approvals: list[dict]) -> None:
        status = str(task.get("status", "unknown"))
        self._status.set_text(f"Task status: {status}")

        if status in {"completed", "failed"}:
            self._spinner.stop()
            self._on_ai_state("idle")
            if status == "completed":
                self._on_notify(AI_TASK_TITLE, "Task completed", "success")
            else:
                self._on_notify(AI_TASK_TITLE, "Task failed", "error")
            self._task_id = None
            self._approval_box.set_visible(False)
            return

        approval = next((a for a in approvals if a.get("task_id") == self._task_id), None)
        if approval:
            self._approval_id = str(approval.get("approval_id", ""))
            self._approval_label.set_text(str(approval.get("reason", "Approval required")))
            self._approval_box.set_visible(True)
            self._on_notify(AI_TASK_TITLE, "Approval needed", "warning")
        else:
            self._approval_id = None
            self._approval_box.set_visible(False)

    def _send_approval(self, approved: bool) -> None:
        if not self._approval_id:
            return

        current = self._approval_id

        def worker() -> None:
            try:
                self._client.submit_approval(current, approved, "via desktop shell")
                GLib.idle_add(self._approval_sent, approved)
            except Exception as exc:
                GLib.idle_add(self._set_error, f"Approval failed: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _approval_sent(self, approved: bool) -> bool:
        self._approval_box.set_visible(False)
        self._approval_id = None
        self._status.set_text("Approval submitted")
        self._on_notify(AI_TASK_TITLE, "Approved" if approved else "Rejected", "info")
        return False
