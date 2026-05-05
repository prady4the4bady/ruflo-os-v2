"""Shell agent: executes local shell commands via asyncio subprocess.

Requires approval under 'require_approval_for_shell' and 'strict' policies.
Commands time out after 30 seconds.
"""
from __future__ import annotations

import asyncio
import shlex
from typing import Any, Dict

from app.agents.base import BaseAgent

_EXEC_TIMEOUT = 30.0


class ShellAgent(BaseAgent):
    agent_type = "shell"

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action == "run":
            command = params.get("command", "")
            if not command:
                return {"status": "error", "error": "No command provided"}
            try:
                parts = shlex.split(command)
                proc = await asyncio.create_subprocess_exec(
                    *parts,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=_EXEC_TIMEOUT
                )
                return {
                    "status": "ok",
                    "exit_code": proc.returncode,
                    "stdout": stdout.decode("utf-8", errors="replace"),
                    "stderr": stderr.decode("utf-8", errors="replace"),
                }
            except asyncio.TimeoutError:
                return {
                    "status": "error",
                    "error": f"Command timed out after {_EXEC_TIMEOUT}s",
                }
            except FileNotFoundError as exc:
                return {"status": "error", "error": str(exc)}

        if action == "which":
            program = params.get("program", "")
            return await self.execute("run", {"command": f"which {program}"})

        return {"status": "unsupported", "action": action}

    def requires_approval(self, action: str, policy: str) -> bool:
        if policy in ("require_approval_for_shell", "strict"):
            return action == "run"
        return False
