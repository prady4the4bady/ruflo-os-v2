"""
Vision module — sends a screenshot to the model-gateway for AI analysis.

The model-gateway is expected to expose a vision-capable chat-completions
endpoint compatible with the OpenAI API shape:
    POST /v1/chat/completions
    { "model": "vision", "messages": [...multimodal content...] }

The screenshot is base64-encoded and embedded as a data-URI image.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

import httpx

MODEL_GATEWAY_URL = os.getenv(
    "MODEL_GATEWAY_URL", "http://model-gateway:8000"
).rstrip("/")

VISION_MODEL = os.getenv("VISION_MODEL", "vision")
_HTTP_TIMEOUT = float(os.getenv("VISION_TIMEOUT_SECS", "30"))


async def describe_screen(screenshot_path: Path, prompt: str) -> str:
    """
    Encode *screenshot_path* as a base64 data-URI and ask the model-gateway
    to answer *prompt* about the visible screen content.

    Returns the model's text response.
    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    image_bytes = Path(screenshot_path).read_bytes()
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    data_uri = f"data:image/png;base64,{image_b64}"

    payload = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": data_uri},
                    },
                ],
            }
        ],
    }

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        response = await client.post(
            f"{MODEL_GATEWAY_URL}/v1/chat/completions",
            json=payload,
        )
        response.raise_for_status()

    data = response.json()
    try:
        return str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError) as exc:
        raise ValueError(
            f"Unexpected model-gateway response shape: {data}"
        ) from exc
