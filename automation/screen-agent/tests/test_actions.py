"""
Unit tests for all /actions/* endpoints.

xdotool subprocess calls are patched out so the tests run without a real
X11 display. Policy gating is disabled (ACTION_POLICY env var unset).
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ── Helpers ──────────────────────────────────────────────────────────────────


def _ok_proc(stdout: str = "") -> MagicMock:
    """Return a completed-process mock that looks like a successful xdotool run."""
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = 0
    proc.stdout = stdout
    proc.stderr = ""
    return proc


# ── POST /actions/mouse-move ─────────────────────────────────────────────────


class TestMouseMove:
    def test_success(self, client: TestClient) -> None:
        with patch("app.actions._run", return_value=_ok_proc()) as mock_run:
            resp = client.post("/actions/mouse-move", json={"x": 100, "y": 200})

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "100" in body["message"] and "200" in body["message"]
        # xdotool mousemove must have been called
        mock_run.assert_called_once_with(["xdotool", "mousemove", "100", "200"])

    def test_xdotool_failure_returns_500(self, client: TestClient) -> None:
        with patch(
            "app.actions._run",
            side_effect=subprocess.CalledProcessError(1, "xdotool", stderr="bad display"),
        ):
            resp = client.post("/actions/mouse-move", json={"x": 0, "y": 0})

        assert resp.status_code == 500
        assert "xdotool" in resp.json()["detail"].lower()

    def test_missing_fields_returns_422(self, client: TestClient) -> None:
        resp = client.post("/actions/mouse-move", json={"x": 10})
        assert resp.status_code == 422


# ── POST /actions/mouse-click ─────────────────────────────────────────────────


class TestMouseClick:
    @pytest.mark.parametrize("button,xdotool_btn", [
        ("left", "1"),
        ("right", "3"),
    ])
    def test_single_click(
        self, client: TestClient, button: str, xdotool_btn: str
    ) -> None:
        calls: list = []

        def fake_run(cmd):
            calls.append(cmd)
            return _ok_proc()

        with patch("app.actions._run", side_effect=fake_run):
            resp = client.post(
                "/actions/mouse-click",
                json={"x": 50, "y": 75, "button": button},
            )

        assert resp.status_code == 200
        # Two calls: mousemove then click
        assert calls[0] == ["xdotool", "mousemove", "50", "75"]
        assert calls[1] == ["xdotool", "click", xdotool_btn]

    def test_double_click(self, client: TestClient) -> None:
        calls: list = []

        def fake_run(cmd):
            calls.append(cmd)
            return _ok_proc()

        with patch("app.actions._run", side_effect=fake_run):
            resp = client.post(
                "/actions/mouse-click",
                json={"x": 10, "y": 20, "button": "double"},
            )

        assert resp.status_code == 200
        assert calls[0] == ["xdotool", "mousemove", "10", "20"]
        # double-click uses --repeat 2
        assert "--repeat" in calls[1]
        assert "2" in calls[1]

    def test_invalid_button_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/actions/mouse-click",
            json={"x": 10, "y": 20, "button": "middle"},
        )
        assert resp.status_code == 422

    def test_xdotool_failure_returns_500(self, client: TestClient) -> None:
        with patch(
            "app.actions._run",
            side_effect=subprocess.CalledProcessError(1, "xdotool", stderr="err"),
        ):
            resp = client.post(
                "/actions/mouse-click", json={"x": 0, "y": 0, "button": "left"}
            )
        assert resp.status_code == 500


# ── POST /actions/keyboard-type ───────────────────────────────────────────────


class TestKeyboardType:
    def test_success(self, client: TestClient) -> None:
        with patch("app.actions._run", return_value=_ok_proc()) as mock_run:
            resp = client.post("/actions/keyboard-type", json={"text": "hello world"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        mock_run.assert_called_once_with(
            ["xdotool", "type", "--clearmodifiers", "--", "hello world"]
        )

    def test_empty_text_accepted(self, client: TestClient) -> None:
        with patch("app.actions._run", return_value=_ok_proc()):
            resp = client.post("/actions/keyboard-type", json={"text": ""})
        assert resp.status_code == 200

    def test_missing_text_returns_422(self, client: TestClient) -> None:
        resp = client.post("/actions/keyboard-type", json={})
        assert resp.status_code == 422

    def test_xdotool_failure_returns_500(self, client: TestClient) -> None:
        with patch(
            "app.actions._run",
            side_effect=subprocess.CalledProcessError(1, "xdotool", stderr="err"),
        ):
            resp = client.post("/actions/keyboard-type", json={"text": "hi"})
        assert resp.status_code == 500


# ── POST /actions/key-combo ───────────────────────────────────────────────────


class TestKeyCombo:
    def test_success(self, client: TestClient) -> None:
        with patch("app.actions._run", return_value=_ok_proc()) as mock_run:
            resp = client.post("/actions/key-combo", json={"keys": ["ctrl", "c"]})

        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_run.assert_called_once_with(["xdotool", "key", "ctrl+c"])

    def test_three_key_combo(self, client: TestClient) -> None:
        with patch("app.actions._run", return_value=_ok_proc()) as mock_run:
            resp = client.post(
                "/actions/key-combo", json={"keys": ["ctrl", "shift", "t"]}
            )
        assert resp.status_code == 200
        mock_run.assert_called_once_with(["xdotool", "key", "ctrl+shift+t"])

    def test_empty_keys_returns_422(self, client: TestClient) -> None:
        resp = client.post("/actions/key-combo", json={"keys": []})
        assert resp.status_code == 422

    def test_xdotool_failure_returns_500(self, client: TestClient) -> None:
        with patch(
            "app.actions._run",
            side_effect=subprocess.CalledProcessError(1, "xdotool", stderr="err"),
        ):
            resp = client.post("/actions/key-combo", json={"keys": ["ctrl", "z"]})
        assert resp.status_code == 500


# ── POST /actions/screenshot ──────────────────────────────────────────────────


class TestScreenshot:
    def test_success(self, client: TestClient, tmp_path: Path) -> None:
        fake_path = tmp_path / "test_20240101_000000_000000.png"
        fake_path.touch()

        with patch("app.actions.take_screenshot", return_value=fake_path) as mock_ss:
            resp = client.post("/actions/screenshot", json={"label": "test"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert str(fake_path) == body["path"]
        mock_ss.assert_called_once_with("test")

    def test_default_label(self, client: TestClient, tmp_path: Path) -> None:
        fake_path = tmp_path / "screenshot_20240101_000000_000000.png"
        fake_path.touch()

        with patch("app.actions.take_screenshot", return_value=fake_path):
            resp = client.post("/actions/screenshot", json={})

        assert resp.status_code == 200

    def test_screenshot_tool_missing_returns_500(self, client: TestClient) -> None:
        with patch(
            "app.actions.take_screenshot",
            side_effect=RuntimeError("No screenshot tool found"),
        ):
            resp = client.post("/actions/screenshot", json={"label": "fail"})
        assert resp.status_code == 500
        assert "screenshot" in resp.json()["detail"].lower()


# ── GET /actions/cursor-pos ───────────────────────────────────────────────────


class TestCursorPos:
    def test_success(self, client: TestClient) -> None:
        with patch(
            "app.actions._run",
            return_value=_ok_proc(stdout="X=320\nY=240\nSCREEN=0\nWINDOW=999\n"),
        ):
            resp = client.get("/actions/cursor-pos")

        assert resp.status_code == 200
        body = resp.json()
        assert body["x"] == 320
        assert body["y"] == 240

    def test_xdotool_failure_returns_500(self, client: TestClient) -> None:
        with patch(
            "app.actions._run",
            side_effect=subprocess.CalledProcessError(1, "xdotool", stderr="no display"),
        ):
            resp = client.get("/actions/cursor-pos")
        assert resp.status_code == 500

    def test_malformed_output_returns_500(self, client: TestClient) -> None:
        with patch("app.actions._run", return_value=_ok_proc(stdout="garbage")):
            resp = client.get("/actions/cursor-pos")
        assert resp.status_code == 500
