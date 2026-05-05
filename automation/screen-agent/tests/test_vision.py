"""
Unit tests for POST /vision/describe-screen and the policy gate.

httpx calls to model-gateway and workflow-engine are intercepted with
respx so no real network traffic occurs.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import create_app


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


# ── POST /vision/describe-screen ──────────────────────────────────────────────


class TestVisionDescribeScreen:
    @respx.mock
    def test_success(self, client: TestClient, tmp_path: Path) -> None:
        fake_png = tmp_path / "vision_20240101_000000_000000.png"
        fake_png.write_bytes(b"\x89PNG\r\n\x1a\n")  # minimal PNG header

        # Mock model-gateway response
        respx.post("http://model-gateway:8000/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "The screen shows a desktop."}}
                    ]
                },
            )
        )

        with patch("app.main.actions.take_screenshot", return_value=fake_png):
            resp = client.post(
                "/vision/describe-screen",
                json={"prompt": "What is on the screen?"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["description"] == "The screen shows a desktop."
        assert str(fake_png) == body["screenshot_path"]

    @respx.mock
    def test_model_gateway_error_returns_502(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        fake_png = tmp_path / "vision_err.png"
        fake_png.write_bytes(b"\x89PNG")

        respx.post("http://model-gateway:8000/v1/chat/completions").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        with patch("app.main.actions.take_screenshot", return_value=fake_png):
            resp = client.post(
                "/vision/describe-screen",
                json={"prompt": "Describe this."},
            )

        assert resp.status_code == 502
        assert "502" in resp.json()["detail"] or "model-gateway" in resp.json()["detail"]

    @respx.mock
    def test_model_gateway_unreachable_returns_502(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        fake_png = tmp_path / "vision_conn.png"
        fake_png.write_bytes(b"\x89PNG")

        respx.post("http://model-gateway:8000/v1/chat/completions").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        with patch("app.main.actions.take_screenshot", return_value=fake_png):
            resp = client.post(
                "/vision/describe-screen",
                json={"prompt": "Describe this."},
            )

        assert resp.status_code == 502
        assert "model-gateway" in resp.json()["detail"].lower()

    def test_screenshot_failure_returns_500(self, client: TestClient) -> None:
        with patch(
            "app.main.actions.take_screenshot",
            side_effect=RuntimeError("No screenshot tool found"),
        ):
            resp = client.post(
                "/vision/describe-screen",
                json={"prompt": "Describe this."},
            )
        assert resp.status_code == 500
        assert "screenshot" in resp.json()["detail"].lower()

    def test_missing_prompt_returns_422(self, client: TestClient) -> None:
        resp = client.post("/vision/describe-screen", json={})
        assert resp.status_code == 422


# ── Policy gate ───────────────────────────────────────────────────────────────


class TestPolicyGate:
    @respx.mock
    def test_action_blocked_when_not_approved(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ACTION_POLICY", "require_approval_for_shell")
        # Re-import policy module to pick up env var change
        import importlib
        import app.policy as policy_mod
        importlib.reload(policy_mod)

        client = TestClient(create_app())

        respx.get("http://workflow-engine:8000/approvals/pending").mock(
            return_value=httpx.Response(
                200, json={"approved": False, "reason": "pending human review"}
            )
        )

        with patch("app.actions._run"):
            resp = client.post("/actions/mouse-move", json={"x": 10, "y": 20})

        assert resp.status_code == 403
        assert "approved" in resp.json()["detail"].lower()

    @respx.mock
    def test_action_allowed_when_approved(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ACTION_POLICY", "require_approval_for_shell")
        import importlib
        import app.policy as policy_mod
        importlib.reload(policy_mod)

        client = TestClient(create_app())

        respx.get("http://workflow-engine:8000/approvals/pending").mock(
            return_value=httpx.Response(200, json={"approved": True})
        )

        with patch("app.actions._run") as mock_run:
            mock_run.return_value = type(
                "CP", (), {"returncode": 0, "stdout": "", "stderr": ""}
            )()
            resp = client.post("/actions/mouse-move", json={"x": 10, "y": 20})

        assert resp.status_code == 200

    def test_no_policy_skips_gate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ACTION_POLICY", raising=False)
        import importlib
        import app.policy as policy_mod
        importlib.reload(policy_mod)

        client = TestClient(create_app())

        # No network mock needed — gate should not call workflow-engine at all
        with patch(
            "app.actions._run",
            return_value=type(
                "CP", (), {"returncode": 0, "stdout": "", "stderr": ""}
            )(),
        ):
            resp = client.post("/actions/mouse-move", json={"x": 5, "y": 5})

        assert resp.status_code == 200
