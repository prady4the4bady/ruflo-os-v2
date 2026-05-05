"""Research agent: drives the Phase 1 model gateway for LLM-powered analysis."""
from __future__ import annotations

import logging
from typing import Any, Dict

import httpx

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    agent_type = "research"

    def __init__(self, gateway_url: str, model: str) -> None:
        self._gateway_url = gateway_url.rstrip("/")
        self._model = model

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action == "summarize":
            content = params.get("content", "")
            question = params.get("question", "Summarize the following content")
            return await self._llm_call(f"{question}:\n\n{content}")

        if action == "analyze":
            content = params.get("content", "")
            return await self._llm_call(
                f"Analyze the following and provide key insights:\n\n{content}"
            )

        if action == "extract_info":
            content = params.get("content", "")
            fields = params.get("fields", [])
            prompt = (
                f"Extract the following information: {', '.join(fields)}\n\nFrom:\n{content}"
            )
            return await self._llm_call(prompt)

        if action == "question":
            context = params.get("context", "")
            question = params.get("question", "")
            return await self._llm_call(f"Context:\n{context}\n\nQuestion: {question}")

        return {"status": "unsupported", "action": action}

    async def _llm_call(self, prompt: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self._gateway_url}/v1/chat/completions",
                    json={
                        "model": self._model,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                return {"status": "ok", "text": text}
        except httpx.HTTPStatusError as exc:
            logger.warning("Gateway HTTP error: %s", exc)
            return {
                "status": "error",
                "error": f"Gateway returned {exc.response.status_code}",
            }
        except Exception as exc:
            logger.warning("Gateway call failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    def requires_approval(self, action: str, policy: str) -> bool:
        return False
