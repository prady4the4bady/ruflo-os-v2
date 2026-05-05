from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


CONFIG_PATH = Path.home() / ".config" / "nemos" / "shell.yaml"


@dataclass
class ShellConfig:
    app_name: str = "Prady"
    logo_text: str = "N"
    theme: str = "dark"
    dock_autohide_delay_ms: int = 1200
    pinned_apps: list[dict[str, str]] = field(
        default_factory=lambda: [
            {"name": "Firefox", "exec": "firefox", "icon": "web-browser"},
            {"name": "Files", "exec": "nautilus", "icon": "folder"},
            {"name": "Terminal", "exec": "gnome-terminal", "icon": "utilities-terminal"},
        ]
    )
    orchestration_url: str = "http://127.0.0.1:11431"

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ShellConfig":
        return ShellConfig(
            app_name=str(data.get("app_name", "Prady")),
            logo_text=str(data.get("logo_text", "N")),
            theme=str(data.get("theme", "dark")),
            dock_autohide_delay_ms=int(data.get("dock_autohide_delay_ms", 1200)),
            pinned_apps=list(data.get("pinned_apps", [])) or ShellConfig().pinned_apps,
            orchestration_url=str(data.get("orchestration_url", "http://127.0.0.1:11431")),
        )


def default_config_dict() -> dict[str, Any]:
    cfg = ShellConfig()
    return {
        "app_name": cfg.app_name,
        "logo_text": cfg.logo_text,
        "theme": cfg.theme,
        "dock_autohide_delay_ms": cfg.dock_autohide_delay_ms,
        "orchestration_url": cfg.orchestration_url,
        "pinned_apps": cfg.pinned_apps,
    }


def ensure_user_config() -> Path:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        with CONFIG_PATH.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(default_config_dict(), fh, sort_keys=False)
    return CONFIG_PATH


def load_config() -> ShellConfig:
    path = ensure_user_config()
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        data = {}
    return ShellConfig.from_dict(data)
