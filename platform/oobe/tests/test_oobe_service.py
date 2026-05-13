from __future__ import annotations

import json
from pathlib import Path

import pytest


def valid_payload() -> dict:
    return {
        "user": {"name": "Kryos User", "username": "kryos_user", "avatar": "avatar-1"},
        "ai": {"model": "llama3-8b", "allow_cloud": False},
        "locale": {"timezone": "UTC", "language": "English", "keyboard": "US"},
    }


@pytest.mark.asyncio
async def test_status_returns_false_before_complete(client) -> None:
    resp = await client.get("/api/oobe/status")
    assert resp.status_code == 200
    assert resp.json() == {"complete": False}


@pytest.mark.asyncio
async def test_oobe_complete_writes_file(client) -> None:
    resp = await client.post("/api/oobe/complete", json=valid_payload())
    assert resp.status_code == 200

    from oobe_service import USER_CONFIG_PATH

    assert USER_CONFIG_PATH.exists()
    payload = json.loads(USER_CONFIG_PATH.read_text(encoding="utf-8"))
    assert payload["user"]["username"] == "kryos_user"


@pytest.mark.asyncio
async def test_status_returns_true_after_complete(client) -> None:
    await client.post("/api/oobe/complete", json=valid_payload())
    resp = await client.get("/api/oobe/status")
    assert resp.status_code == 200
    assert resp.json() == {"complete": True}


@pytest.mark.asyncio
async def test_payload_validation_username(client) -> None:
    payload = valid_payload()
    payload["user"]["username"] = "Invalid-Name"
    resp = await client.post("/api/oobe/complete", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_422_on_bad_data(client) -> None:
    resp = await client.post("/api/oobe/complete", json={"bad": "payload"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_oobe_route_serves_index(client) -> None:
    resp = await client.get("/oobe")
    assert resp.status_code == 200
    assert "oobe" in resp.text


# ---------------------------------------------------------------------------
# Credential validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_openai_missing_key(client) -> None:
    resp = await client.post(
        "/api/oobe/validate-credential",
        json={"provider": "openai"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "openai"
    assert body["valid"] is False
    assert "api_key" in body["detail"]


@pytest.mark.asyncio
async def test_validate_openai_happy_path(client, respx_mock) -> None:
    import respx
    from httpx import Response

    respx_mock.get("https://api.openai.com/v1/models").mock(
        return_value=Response(200, json={"data": []})
    )
    resp = await client.post(
        "/api/oobe/validate-credential",
        json={"provider": "openai", "api_key": "sk-test"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert body["detail"] == "ok"


@pytest.mark.asyncio
async def test_validate_openai_rejects_bad_key(client, respx_mock) -> None:
    from httpx import Response

    respx_mock.get("https://api.openai.com/v1/models").mock(
        return_value=Response(401, json={"error": "invalid"})
    )
    resp = await client.post(
        "/api/oobe/validate-credential",
        json={"provider": "openai", "api_key": "sk-bad"},
    )
    body = resp.json()
    assert body["valid"] is False
    assert "401" in body["detail"]


@pytest.mark.asyncio
async def test_validate_huggingface_happy(client, respx_mock) -> None:
    from httpx import Response

    respx_mock.get("https://huggingface.co/api/whoami-v2").mock(
        return_value=Response(200, json={"name": "someuser"})
    )
    resp = await client.post(
        "/api/oobe/validate-credential",
        json={"provider": "huggingface", "api_key": "hf_token"},
    )
    body = resp.json()
    assert body["valid"] is True
    assert "someuser" in body["detail"]


@pytest.mark.asyncio
async def test_validate_anthropic_billing_still_valid(client, respx_mock) -> None:
    # A 403 from Anthropic when the key itself is valid but billing is
    # exhausted should NOT be reported as an invalid credential. The
    # OOBE wizard tells the user the key works so they can continue
    # and handle billing separately.
    from httpx import Response

    respx_mock.post("https://api.anthropic.com/v1/messages").mock(
        return_value=Response(403, json={"error": "billing"})
    )
    resp = await client.post(
        "/api/oobe/validate-credential",
        json={"provider": "anthropic", "api_key": "sk-ant-test"},
    )
    body = resp.json()
    assert body["valid"] is True
    assert "403" in body["detail"]


@pytest.mark.asyncio
async def test_validate_ollama_reachable(client, respx_mock) -> None:
    from httpx import Response

    respx_mock.get("http://localhost:11434/api/tags").mock(
        return_value=Response(200, json={"models": [{"name": "llama3"}]})
    )
    resp = await client.post(
        "/api/oobe/validate-credential",
        json={"provider": "ollama"},
    )
    body = resp.json()
    assert body["valid"] is True
    assert "1 local" in body["detail"]


@pytest.mark.asyncio
async def test_validate_ollama_unreachable(client) -> None:
    # No mock registered, respx blocks the network call; the service
    # should surface a friendly "not reachable" error rather than 500.
    resp = await client.post(
        "/api/oobe/validate-credential",
        json={"provider": "ollama", "base_url": "http://not-there:11434"},
    )
    body = resp.json()
    assert body["valid"] is False
    assert "not reachable" in body["detail"]


@pytest.mark.asyncio
async def test_validate_github_anonymous(client, respx_mock) -> None:
    from httpx import Response

    respx_mock.get("https://api.github.com/rate_limit").mock(
        return_value=Response(200, json={"rate": {"remaining": 60}})
    )
    resp = await client.post(
        "/api/oobe/validate-credential",
        json={"provider": "github"},
    )
    body = resp.json()
    assert body["valid"] is True
    assert "anonymous" in body["detail"]


@pytest.mark.asyncio
async def test_validate_github_authenticated(client, respx_mock) -> None:
    from httpx import Response

    respx_mock.get("https://api.github.com/user").mock(
        return_value=Response(200, json={"login": "me"})
    )
    resp = await client.post(
        "/api/oobe/validate-credential",
        json={"provider": "github", "api_key": "ghp_xxx"},
    )
    body = resp.json()
    assert body["valid"] is True
    assert "me" in body["detail"]


@pytest.mark.asyncio
async def test_validate_rejects_unknown_provider(client) -> None:
    resp = await client.post(
        "/api/oobe/validate-credential",
        json={"provider": "madeup", "api_key": "x"},
    )
    # FastAPI Literal validation kicks in first.
    assert resp.status_code == 422
