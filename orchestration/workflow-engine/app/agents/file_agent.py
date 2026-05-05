"""File agent: async read / write / list operations on the local filesystem."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import aiofiles

from app.agents.base import BaseAgent


class FileAgent(BaseAgent):
    agent_type = "file"

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action == "read":
            path = params.get("path", "")
            expanded = str(Path(path).expanduser())
            try:
                async with aiofiles.open(expanded, encoding="utf-8") as fh:
                    content = await fh.read()
                return {"status": "ok", "path": expanded, "content": content, "size": len(content)}
            except Exception as exc:
                return {"status": "error", "error": str(exc)}

        if action == "write":
            path = params.get("path", "")
            expanded = str(Path(path).expanduser())
            content = params.get("content", "")
            try:
                Path(expanded).parent.mkdir(parents=True, exist_ok=True)
                async with aiofiles.open(expanded, "w", encoding="utf-8") as fh:
                    await fh.write(content)
                return {"status": "ok", "path": expanded, "bytes_written": len(content)}
            except Exception as exc:
                return {"status": "error", "error": str(exc)}

        if action == "list":
            path = params.get("path", ".")
            expanded = str(Path(path).expanduser())
            try:
                entries = [str(p) for p in Path(expanded).iterdir()]
                return {"status": "ok", "path": expanded, "entries": entries}
            except Exception as exc:
                return {"status": "error", "error": str(exc)}

        if action == "exists":
            path = params.get("path", "")
            expanded = str(Path(path).expanduser())
            return {"status": "ok", "path": expanded, "exists": Path(expanded).exists()}

        return {"status": "unsupported", "action": action}

    def requires_approval(self, action: str, policy: str) -> bool:
        if policy == "strict":
            return action in ("write", "delete")
        return False
