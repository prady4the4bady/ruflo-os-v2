import base64
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
from typing import Any


NO_DISPLAY_SERVER = "no display server detected"
XDOTOOL_MISSING = "xdotool is not installed"


def _has_python_xlib() -> bool:
    try:
        import Xlib  # type: ignore

        return True
    except Exception:
        return False


def detect_display_server(env: dict[str, str] | None = None) -> str:
    values = env or os.environ
    if values.get("WAYLAND_DISPLAY"):
        return "wayland"
    if values.get("DISPLAY"):
        return "x11"
    return "none"


class ActionExecutor:
    def __init__(self, env: dict[str, str] | None = None) -> None:
        self._env = env or os.environ
        self.display_server = detect_display_server(self._env)
        self.available_tools = {
            "ydotool": shutil.which("ydotool") is not None,
            "xdotool": shutil.which("xdotool") is not None,
            "grim": shutil.which("grim") is not None,
            "scrot": shutil.which("scrot") is not None,
            "python_xlib": _has_python_xlib(),
        }

    def _run(self, args: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=self._env,
            check=False,
        )

    def _run_wayland_or_fail(self, args: list[str]) -> tuple[bool, str]:
        if not self.available_tools["ydotool"]:
            return False, "ydotool is not installed"

        proc = self._run(args)
        if proc.returncode == 0:
            return True, "ok"

        stderr = (proc.stderr or "").strip()
        if "socket" in stderr.lower() or "daemon" in stderr.lower():
            return False, "ydotoold is unavailable; start ydotoold and retry"
        return False, stderr or "ydotool command failed"

    def click(self, x: int, y: int) -> tuple[bool, str]:
        if self.display_server == "wayland":
            ok, msg = self._run_wayland_or_fail(["ydotool", "mousemove", "--absolute", str(x), str(y)])
            if not ok:
                return False, msg
            return self._run_wayland_or_fail(["ydotool", "click", "0xC0"])

        if self.display_server == "x11":
            if not self.available_tools["xdotool"]:
                return False, XDOTOOL_MISSING
            if not self.available_tools["python_xlib"]:
                return False, "python-xlib is unavailable"
            proc = self._run(["xdotool", "mousemove", str(x), str(y), "click", "1"])
            return proc.returncode == 0, (proc.stderr or "ok").strip()

        return False, NO_DISPLAY_SERVER

    def type_text(self, text: str) -> tuple[bool, str]:
        if self.display_server == "wayland":
            return self._run_wayland_or_fail(["ydotool", "type", "--", text])

        if self.display_server == "x11":
            if not self.available_tools["xdotool"]:
                return False, XDOTOOL_MISSING
            proc = self._run(["xdotool", "type", "--delay", "1", text])
            return proc.returncode == 0, (proc.stderr or "ok").strip()

        return False, NO_DISPLAY_SERVER

    def key(self, keys: list[str]) -> tuple[bool, str]:
        if self.display_server == "wayland":
            combo = "+".join(keys)
            return self._run_wayland_or_fail(["ydotool", "key", combo])

        if self.display_server == "x11":
            if not self.available_tools["xdotool"]:
                return False, XDOTOOL_MISSING
            proc = self._run(["xdotool", "key", "+".join(keys)])
            return proc.returncode == 0, (proc.stderr or "ok").strip()

        return False, NO_DISPLAY_SERVER

    def open_app(self, app: str) -> tuple[bool, str]:
        args = shlex.split(app)
        if not args:
            return False, "invalid app command"
        try:
            subprocess.Popen(args, env=self._env)
            return True, "ok"
        except Exception as exc:
            return False, str(exc)

    def screenshot(self) -> tuple[bool, str, str | None]:
        if self.display_server == "wayland" and self.available_tools["grim"]:
            proc = subprocess.run(
                ["grim", "-"],
                capture_output=True,
                timeout=10.0,
                check=False,
                env=self._env,
            )
            if proc.returncode == 0:
                return True, "ok", base64.b64encode(proc.stdout).decode("ascii")
            return False, (proc.stderr.decode("utf-8", errors="ignore") or "grim failed").strip(), None

        if self.available_tools["scrot"]:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                path = Path(tmp.name)
            try:
                proc = self._run(["scrot", str(path)])
                if proc.returncode != 0:
                    return False, (proc.stderr or "scrot failed").strip(), None
                payload = base64.b64encode(path.read_bytes()).decode("ascii")
                return True, "ok", payload
            finally:
                if path.exists():
                    path.unlink()

        return False, "no screenshot tool found (grim/scrot)", None

    def execute(self, action_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if action_type == "click":
            success, message = self.click(int(payload["x"]), int(payload["y"]))
            return {"success": success, "message": message}
        if action_type == "type":
            success, message = self.type_text(str(payload["text"]))
            return {"success": success, "message": message}
        if action_type == "key":
            success, message = self.key(list(payload["keys"]))
            return {"success": success, "message": message}
        if action_type == "open_app":
            success, message = self.open_app(str(payload["app"]))
            return {"success": success, "message": message}
        if action_type == "screenshot":
            success, message, image = self.screenshot()
            return {"success": success, "message": message, "screenshot_base64": image}
        return {"success": False, "message": f"unsupported action: {action_type}"}
