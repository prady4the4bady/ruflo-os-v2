"""Tests for NVIDIA NIM, Gemini, and vLLM backends in ModelGateway."""

from __future__ import annotations

import json
import os

import pytest
import respx
from httpx import Response

from app.gateway import GatewayError, ModelGateway
from app.schemas import ChatCompletionRequest, ChatMessage
from tests.conftest import make_gateway

pytestmark = pytest.mark.anyio

CHAT_MESSAGES = [ChatMessage(role="user", content="Hello")]
NVIDIA_NIM_CONFIG_KEY = "NVIDIA_NIM_API_KEY"
GEMINI_CONFIG_KEY = "GEMINI_API_KEY"
VLLM_CONFIG_KEY = "VLLM_API_KEY"


def _openai_response(model: str = "nvidia-model") -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1700000000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello from NIM!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
    }


def _gemini_response() -> dict:
    return {
        "candidates": [
            {
                "content": {"parts": [{"text": "Hello from Gemini!"}], "role": "model"},
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 5},
    }


# ---------------------------------------------------------------------------
# NVIDIA NIM
# ---------------------------------------------------------------------------


@respx.mock
async def test_nim_success(policy_local_first, audit_logger):
    os.environ[NVIDIA_NIM_CONFIG_KEY] = "test-nim-key"
    try:
        gw = make_gateway(policy_local_first, audit_logger)

        respx.post("https://api.nvcf.nvidia.com/v1/chat/completions").mock(
            return_value=Response(200, json=_openai_response("nvidia/llama-nemotron"))
        )

        req = ChatCompletionRequest(
            model="nvidia/llama-nemotron", messages=CHAT_MESSAGES
        )
        resp = await gw.chat_completion(req, correlation_id="nim-test")

        assert resp.model == "nvidia/llama-nemotron"
        assert resp.choices[0].message.content == "Hello from NIM!"
    finally:
        os.environ.pop(NVIDIA_NIM_CONFIG_KEY, None)


@respx.mock
async def test_nim_missing_key_raises_503(policy_cloud_only, audit_logger):
    os.environ.pop(NVIDIA_NIM_CONFIG_KEY, None)

    policy_cloud_only.mode = "cloud-only"
    gw = make_gateway(policy_cloud_only, audit_logger)

    req = ChatCompletionRequest(model="nvidia/llama-nemotron", messages=CHAT_MESSAGES)
    with pytest.raises(GatewayError) as exc_info:
        await gw.chat_completion(req, correlation_id="nim-nokey")

    assert exc_info.value.status_code == 503


@respx.mock
async def test_nim_fallback_from_local(policy_local_first, audit_logger):
    """When Ollama fails, local-first should try NIM if in fallback_order."""
    os.environ[NVIDIA_NIM_CONFIG_KEY] = "test-nim-key"
    try:
        gw = make_gateway(policy_local_first, audit_logger)

        respx.post("http://localhost:11434/v1/chat/completions").mock(
            return_value=Response(500, json={"error": "model not loaded"})
        )
        respx.post("https://api.nvcf.nvidia.com/v1/chat/completions").mock(
            return_value=Response(200, json=_openai_response("nvidia/llama-nemotron"))
        )

        req = ChatCompletionRequest(
            model="nvidia/llama-nemotron", messages=CHAT_MESSAGES
        )
        resp = await gw.chat_completion(req, correlation_id="nim-fallback")

        assert resp.choices[0].message.content == "Hello from NIM!"
    finally:
        os.environ.pop(NVIDIA_NIM_CONFIG_KEY, None)


# ---------------------------------------------------------------------------
# Google Gemini
# ---------------------------------------------------------------------------


@respx.mock
async def test_gemini_success(policy_local_first, audit_logger):
    os.environ[GEMINI_CONFIG_KEY] = "test-gemini-key"
    try:
        gw = make_gateway(policy_local_first, audit_logger)

        respx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        ).mock(return_value=Response(200, json=_gemini_response()))

        req = ChatCompletionRequest(model="gemini-2.0-flash", messages=CHAT_MESSAGES)
        resp = await gw.chat_completion(req, correlation_id="gemini-test")

        assert resp.choices[0].message.content == "Hello from Gemini!"
    finally:
        os.environ.pop(GEMINI_CONFIG_KEY, None)


@respx.mock
async def test_gemini_missing_key_raises_503(policy_cloud_only, audit_logger):
    os.environ.pop(GEMINI_CONFIG_KEY, None)

    gw = make_gateway(policy_cloud_only, audit_logger)

    req = ChatCompletionRequest(model="gemini-2.0-flash", messages=CHAT_MESSAGES)
    with pytest.raises(GatewayError) as exc_info:
        await gw.chat_completion(req, correlation_id="gemini-nokey")

    assert exc_info.value.status_code == 503


@respx.mock
async def test_gemini_system_instruction(policy_cloud_only, audit_logger):
    """System messages become top-level systemInstruction for Gemini."""
    os.environ[GEMINI_CONFIG_KEY] = "test-gemini-key"
    try:
        gw = make_gateway(policy_cloud_only, audit_logger)

        captured: list[dict] = []

        def capture(request, route):
            captured.append(json.loads(request.content))
            return Response(200, json=_gemini_response())

        respx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        ).mock(side_effect=capture)

        req = ChatCompletionRequest(
            model="gemini-2.0-flash",
            messages=[
                ChatMessage(role="system", content="You are a helpful assistant."),
                ChatMessage(role="user", content="Hello"),
            ],
        )
        resp = await gw.chat_completion(req, correlation_id="gemini-sys")

        assert len(captured) == 1
        payload = captured[0]
        assert payload["systemInstruction"]["parts"][0]["text"] == "You are a helpful assistant."
        assert all(m["role"] != "system" for m in payload["contents"])
        assert resp.choices[0].message.content == "Hello from Gemini!"
    finally:
        os.environ.pop(GEMINI_CONFIG_KEY, None)


# ---------------------------------------------------------------------------
# vLLM (OpenAI-compatible)
# ---------------------------------------------------------------------------


@respx.mock
async def test_vllm_success(policy_local_first, audit_logger):
    os.environ[VLLM_CONFIG_KEY] = "test-vllm-key"
    os.environ["OPENAI_API_KEY"] = "test-key"
    try:
        gw = make_gateway(policy_local_first, audit_logger)

        respx.post("http://localhost:11434/v1/chat/completions").mock(
            return_value=Response(500, json={"error": "ollama down"})
        )
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=Response(500, json={"error": "openai down"})
        )
        respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=Response(500, json={"error": "anthropic down"})
        )

        req = ChatCompletionRequest(
            model="Qwen/Qwen2.5-7B-Instruct", messages=CHAT_MESSAGES
        )
        # vllm is not in fallback_order, so this must fail with all backends exhausted
        with pytest.raises(GatewayError):
            await gw.chat_completion(req, correlation_id="vllm-test")
    finally:
        os.environ.pop(VLLM_CONFIG_KEY, None)
        os.environ.pop("OPENAI_API_KEY", None)


@respx.mock
async def test_vllm_direct_dispatch(policy_local_first, audit_logger):
    """Test vLLM backend directly via _dispatch_chat, bypassing routing."""
    from app.config import ProviderConfig

    os.environ[VLLM_CONFIG_KEY] = "test-vllm-key"
    try:
        gw = make_gateway(policy_local_first, audit_logger)

        respx.post("http://localhost:8000/chat/completions").mock(
            return_value=Response(
                200, json=_openai_response("Qwen/Qwen2.5-7B-Instruct")
            )
        )

        cfg = ProviderConfig("vllm", {
            "base_url": "http://localhost:8000",
            "env_key": VLLM_CONFIG_KEY,
            "timeout_seconds": 60,
        })

        req = ChatCompletionRequest(
            model="Qwen/Qwen2.5-7B-Instruct", messages=CHAT_MESSAGES
        )
        resp = await gw._dispatch_chat("vllm", cfg, req, "vllm-direct")

        assert resp.model == "Qwen/Qwen2.5-7B-Instruct"
        assert resp.choices[0].message.content == "Hello from NIM!"
    finally:
        os.environ.pop(VLLM_CONFIG_KEY, None)
