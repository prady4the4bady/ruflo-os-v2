"""Tests for ModelGateway using respx to mock httpx."""

from __future__ import annotations

import json
import uuid

import pytest
import respx
from httpx import Response

from app.gateway import GatewayError, ModelGateway
from app.policy import RoutingPolicyEngine
from app.schemas import ChatCompletionRequest, ChatMessage
from tests.conftest import make_gateway

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CHAT_MESSAGES = [ChatMessage(role="user", content="Hello")]


def _openai_response(model: str = "gpt-4o") -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1700000000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hi there!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
    }


def _anthropic_response(model: str = "claude-3-5-sonnet-20241022") -> dict:
    return {
        "id": "msg-test",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": "Hello!"}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 5, "output_tokens": 5},
    }


# ---------------------------------------------------------------------------
# Ollama success
# ---------------------------------------------------------------------------


@respx.mock
async def test_chat_ollama_success(policy_local_first, audit_logger):
    gw = make_gateway(policy_local_first, audit_logger)

    respx.post("http://localhost:11434/v1/chat/completions").mock(
        return_value=Response(200, json=_openai_response("llama3.2:3b"))
    )

    req = ChatCompletionRequest(model="llama3.2:3b", messages=CHAT_MESSAGES)
    resp = await gw.chat_completion(req, correlation_id="test-cid")

    assert resp.model == "llama3.2:3b"
    assert resp.choices[0].message.content == "Hi there!"


# ---------------------------------------------------------------------------
# local-first fallback to openai when ollama fails
# ---------------------------------------------------------------------------


@respx.mock
async def test_chat_local_first_fallback_to_openai(policy_local_first, audit_logger):
    gw = make_gateway(policy_local_first, audit_logger)

    import os

    os.environ["OPENAI_API_KEY"] = "test-key"
    try:
        respx.post("http://localhost:11434/v1/chat/completions").mock(
            return_value=Response(500, json={"error": "model not loaded"})
        )
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=Response(200, json=_openai_response("gpt-4o"))
        )

        req = ChatCompletionRequest(model="gpt-4o", messages=CHAT_MESSAGES)
        resp = await gw.chat_completion(req, correlation_id="test-cid-2")

        assert resp.choices[0].message.content == "Hi there!"
    finally:
        os.environ.pop("OPENAI_API_KEY", None)


# ---------------------------------------------------------------------------
# local-only blocks fallback when ollama fails
# ---------------------------------------------------------------------------


@respx.mock
async def test_chat_local_only_blocks_when_ollama_down(policy_local_only, audit_logger):
    gw = make_gateway(policy_local_only, audit_logger)

    respx.post("http://localhost:11434/v1/chat/completions").mock(
        return_value=Response(503, json={"error": "service unavailable"})
    )

    req = ChatCompletionRequest(model="llama3.2:3b", messages=CHAT_MESSAGES)
    with pytest.raises(GatewayError) as exc_info:
        await gw.chat_completion(req, correlation_id="cid-local-only")

    assert exc_info.value.status_code == 503
    assert "local-only" in str(exc_info.value)


# ---------------------------------------------------------------------------
# all backends fail → 503
# ---------------------------------------------------------------------------


@respx.mock
async def test_chat_all_backends_fail(policy_local_first, audit_logger):
    import os

    os.environ["OPENAI_API_KEY"] = "test-key"
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    try:
        gw = make_gateway(policy_local_first, audit_logger)

        respx.post("http://localhost:11434/v1/chat/completions").mock(
            return_value=Response(500)
        )
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=Response(500)
        )
        respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=Response(500)
        )

        req = ChatCompletionRequest(model="llama3.2:3b", messages=CHAT_MESSAGES)
        with pytest.raises(GatewayError) as exc_info:
            await gw.chat_completion(req, correlation_id="cid-all-fail")

        assert exc_info.value.status_code == 503
    finally:
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)


# ---------------------------------------------------------------------------
# Anthropic message conversion – system role extracted
# ---------------------------------------------------------------------------


@respx.mock
async def test_anthropic_system_message_extracted(policy_cloud_only, audit_logger):
    import os

    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    try:
        gw = make_gateway(policy_cloud_only, audit_logger)

        captured: list[dict] = []

        def capture(request, route):  # type: ignore[no-untyped-def]
            captured.append(json.loads(request.content))
            return Response(
                200,
                json=_anthropic_response("claude-3-5-sonnet-20241022"),
            )

        respx.post("https://api.anthropic.com/v1/messages").mock(side_effect=capture)

        req = ChatCompletionRequest(
            model="claude-3-5-sonnet-20241022",
            messages=[
                ChatMessage(role="system", content="You are a helpful assistant."),
                ChatMessage(role="user", content="Hello"),
            ],
        )
        resp = await gw.chat_completion(req, correlation_id="cid-anthropic")

        assert len(captured) == 1
        payload = captured[0]
        # system role must be top-level, not inside messages
        assert payload["system"] == "You are a helpful assistant."
        assert all(m["role"] != "system" for m in payload["messages"])
        assert resp.choices[0].message.content == "Hello!"
    finally:
        os.environ.pop("ANTHROPIC_API_KEY", None)


# ---------------------------------------------------------------------------
# Missing API key → GatewayError 503
# ---------------------------------------------------------------------------


@respx.mock
async def test_openai_missing_key_raises_503(policy_cloud_only, audit_logger):
    import os

    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("ANTHROPIC_API_KEY", None)

    gw = make_gateway(policy_cloud_only, audit_logger)

    req = ChatCompletionRequest(model="gpt-4o", messages=CHAT_MESSAGES)
    with pytest.raises(GatewayError) as exc_info:
        await gw.chat_completion(req, correlation_id="cid-nokey")

    # Should exhaust cloud backends (all missing keys → GatewayError skipping to 503)
    assert exc_info.value.status_code in (503, 403)
