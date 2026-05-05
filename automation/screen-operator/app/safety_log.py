import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


class ActionLogger:
    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._recent: list[dict[str, Any]] = []

    def log(self, action_type: str, params: dict[str, Any], success: bool, message: str = "") -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": action_type,
            "params": params,
            "success": success,
            "message": message,
        }
        line = json.dumps(record, ensure_ascii=True)
        with self._lock:
            with self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
            self._recent.append(record)
            if len(self._recent) > 5:
                self._recent = self._recent[-5:]

    def last_actions(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._recent)
