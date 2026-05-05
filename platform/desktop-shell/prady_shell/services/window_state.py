from __future__ import annotations

import subprocess
from typing import Optional


class ActiveWindowService:
    def _run(self, cmd: list[str]) -> str:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=2.0)
        if proc.returncode != 0:
            return ""
        return (proc.stdout or "").strip()

    def focused_app_name(self) -> str:
        hypr = self._run(["hyprctl", "activewindow", "-j"])
        if hypr:
            try:
                import json

                payload = json.loads(hypr)
                app_name = payload.get("class") or payload.get("title")
                if app_name:
                    return str(app_name)
            except Exception:
                pass

        window_id = self._run(["xdotool", "getwindowfocus"])
        if window_id:
            title = self._run(["xdotool", "getwindowname", window_id])
            if title:
                return title

        return "Desktop"


class SystemStatusService:
    def battery(self) -> str:
        upower_output = self._run_optional(["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"])
        if upower_output:
            for line in upower_output.splitlines():
                if "percentage" in line:
                    return line.split(":", 1)[-1].strip()
        return "--%"

    def wifi(self) -> str:
        nmcli_output = self._run_optional(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"])
        if nmcli_output:
            for line in nmcli_output.splitlines():
                if line.startswith("yes:"):
                    return line.split(":", 1)[1] or "WiFi"
        return "Offline"

    def _run_optional(self, cmd: list[str]) -> str:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=2.0)
            if proc.returncode == 0:
                return (proc.stdout or "").strip()
        except Exception:
            return ""
        return ""
