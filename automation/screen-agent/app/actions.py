"""
Low-level input control and screenshot capture.

Mouse / keyboard actions delegate to xdotool (subprocess).
Screenshot capture uses scrot > gnome-screenshot > ImageMagick import,
in that preference order.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

SCREENSHOTS_DIR = Path("/tmp/screenshots")

# ── Internal helpers ─────────────────────────────────────────────────────────


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run *cmd*, raise CalledProcessError on non-zero exit, capture output."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
    )


# ── Mouse actions ────────────────────────────────────────────────────────────


def mouse_move(x: int, y: int) -> None:
    """Move the cursor to absolute screen coordinates (*x*, *y*)."""
    _run(["xdotool", "mousemove", str(x), str(y)])


def mouse_click(x: int, y: int, button: str) -> None:
    """
    Move cursor to (*x*, *y*) and click.

    button: "left" → button 1, "right" → button 3, "double" → double-click left.
    """
    btn_map = {"left": "1", "right": "3", "double": "1"}
    btn_code = btn_map[button]

    _run(["xdotool", "mousemove", str(x), str(y)])

    if button == "double":
        _run(["xdotool", "click", "--repeat", "2", "--delay", "50", btn_code])
    else:
        _run(["xdotool", "click", btn_code])


# ── Keyboard actions ─────────────────────────────────────────────────────────


def keyboard_type(text: str) -> None:
    """
    Type *text* as if entered from the keyboard.

    Uses xdotool type with --clearmodifiers so any held modifier keys
    (e.g. Shift) do not corrupt the typed string.
    """
    _run(["xdotool", "type", "--clearmodifiers", "--", text])


def key_combo(keys: list[str]) -> None:
    """
    Send a key combination.

    *keys* is an ordered list such as ``["ctrl", "shift", "t"]``.
    The list is joined with ``+`` to form the xdotool key sequence.
    """
    combo = "+".join(keys)
    _run(["xdotool", "key", combo])


# ── Cursor position ──────────────────────────────────────────────────────────


def cursor_pos() -> tuple[int, int]:
    """Return the current cursor position as (x, y)."""
    result = _run(["xdotool", "getmouselocation", "--shell"])
    # Output looks like: X=800\nY=600\nSCREEN=0\nWINDOW=12345\n
    x_match = re.search(r"X=(\d+)", result.stdout)
    y_match = re.search(r"Y=(\d+)", result.stdout)
    if not x_match or not y_match:
        raise RuntimeError(
            f"Could not parse xdotool output: {result.stdout!r}"
        )
    return int(x_match.group(1)), int(y_match.group(1))


# ── Screenshot ───────────────────────────────────────────────────────────────


def _safe_label(label: str) -> str:
    """Strip characters unsafe for filenames."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", label)


def take_screenshot(label: str = "screenshot") -> Path:
    """
    Capture a full-screen PNG to ``/tmp/screenshots/{label}_{timestamp}.png``.

    Tries (in order): scrot → gnome-screenshot → ImageMagick import.
    Raises RuntimeError if none are available.
    """
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{_safe_label(label)}_{timestamp}.png"
    path = SCREENSHOTS_DIR / filename

    if shutil.which("scrot"):
        _run(["scrot", str(path)])
    elif shutil.which("gnome-screenshot"):
        _run(["gnome-screenshot", "--file", str(path)])
    elif shutil.which("import"):  # ImageMagick
        _run(["import", "-window", "root", str(path)])
    else:
        raise RuntimeError(
            "No screenshot tool found; install scrot, gnome-screenshot, or ImageMagick."
        )

    return path
