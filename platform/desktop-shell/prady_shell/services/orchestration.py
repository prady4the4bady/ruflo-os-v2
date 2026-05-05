from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class OrchestrationClient:
    base_url: str

    def submit_goal(self, goal: str) -> dict[str, Any]:
        response = httpx.post(f"{self.base_url}/tasks", json={"goal": goal, "policy": "default"}, timeout=15.0)
        response.raise_for_status()
        return response.json()

    def get_task(self, task_id: str) -> dict[str, Any]:
        response = httpx.get(f"{self.base_url}/tasks/{task_id}", timeout=10.0)
        response.raise_for_status()
        return response.json()

    def pending_approvals(self) -> list[dict[str, Any]]:
        response = httpx.get(f"{self.base_url}/approvals/pending", timeout=10.0)
        response.raise_for_status()
        body = response.json()
        return list(body.get("pending", []))

    def submit_approval(self, approval_id: str, approved: bool, reviewer_note: str = "") -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/approvals/submit",
            json={"approval_id": approval_id, "approved": approved, "reviewer_note": reviewer_note},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()
