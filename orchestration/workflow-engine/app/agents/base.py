"""Abstract base class for all sub-agents."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):
    agent_type: str = "base"

    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute *action* with *params* and return a result dict."""
        ...

    def requires_approval(self, action: str, policy: str) -> bool:
        """Return True if this action needs human confirmation under *policy*."""
        return False
