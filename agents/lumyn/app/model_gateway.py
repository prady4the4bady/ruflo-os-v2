from __future__ import annotations

from typing import Any

import httpx


class GatewayClient:
    def __init__(self, base_url: str, timeout: float = 60.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def list_models(self) -> list[str]:
        resp = await self._client.get(f"{self._base_url}/v1/models")
        resp.raise_for_status()
        body = resp.json()
        return [m["id"] for m in body.get("data", []) if isinstance(m, dict) and "id" in m]

    async def chat(self, *, prompt: str, model: str | None = None, temperature: float = 0.2) -> str:
        chosen_model = model
        if not chosen_model:
            models = await self.list_models()
            if not models:
                raise RuntimeError("No models are registered in model-gateway")
            chosen_model = models[0]

        payload: dict[str, Any] = {
            "model": chosen_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        resp = await self._client.post(f"{self._base_url}/v1/chat/completions", json=payload)
        resp.raise_for_status()
        body = resp.json()
        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("Model returned no choices")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError("Model response missing text content")
        return content
