from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

CONFIG_DIR = Path(os.getenv("KRYOS_CONFIG_DIR", "/opt/kryos-os/config"))
USER_CONFIG_PATH = CONFIG_DIR / "user.json"
OOBE_MARKER_PATH = CONFIG_DIR / ".oobe_complete"
OOBE_DIST = Path(os.getenv("OOBE_DIST", "/opt/kryos-os/ui/oobe-wizard/dist"))

_VALIDATION_TIMEOUT_SECS = float(os.getenv("OOBE_VALIDATION_TIMEOUT_SECS", "10"))


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class UserModel(BaseModel):
    name: str = Field(min_length=1)
    username: str = Field(min_length=3, max_length=20)
    avatar: str = Field(min_length=1)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"[a-z0-9_]{3,20}", value):
            raise ValueError("username must match [a-z0-9_]{3,20}")
        return value


class AIModel(BaseModel):
    model: str = Field(min_length=1)
    allow_cloud: bool


class LocaleModel(BaseModel):
    timezone: str = Field(min_length=1)
    language: Literal["English", "Spanish", "French", "German", "Japanese"]
    keyboard: Literal["US", "UK", "German", "French", "Japanese"]


class OOBEPayload(BaseModel):
    user: UserModel
    ai: AIModel
    locale: LocaleModel


class CredentialValidateRequest(BaseModel):
    """Request to probe a single provider's credential."""

    provider: Literal[
        "openai",
        "anthropic",
        "huggingface",
        "ollama",
        "github",
    ]
    api_key: Optional[str] = None
    # For providers that aren't API-key-based (Ollama), the user
    # supplies the base URL instead.
    base_url: Optional[str] = None


class CredentialValidateResponse(BaseModel):
    provider: str
    valid: bool
    detail: str
    probed_url: Optional[str] = None


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


app = FastAPI(title="Kryos OOBE Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

ASSETS_DIR = OOBE_DIST / "assets"
if ASSETS_DIR.exists():
    app.mount("/oobe/assets", StaticFiles(directory=ASSETS_DIR), name="oobe-assets")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/oobe/status")
async def oobe_status() -> dict[str, bool]:
    return {"complete": OOBE_MARKER_PATH.exists()}


@app.post("/api/oobe/complete")
async def oobe_complete(payload: OOBEPayload) -> dict[str, str]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    with USER_CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload.model_dump(), f, indent=2)

    os.chmod(USER_CONFIG_PATH, 0o600)
    OOBE_MARKER_PATH.write_text("complete\n", encoding="utf-8")
    os.chmod(OOBE_MARKER_PATH, 0o600)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Credential validation
# ---------------------------------------------------------------------------


@app.post(
    "/api/oobe/validate-credential", response_model=CredentialValidateResponse
)
async def validate_credential(
    req: CredentialValidateRequest,
) -> CredentialValidateResponse:
    """Probe a single provider's credential with a small, idempotent
    read-only request. Returns valid=True only if the provider
    returned a positive response within the timeout. Never stores
    the credential.
    """
    if req.provider == "openai":
        return await _probe_openai(req.api_key)
    if req.provider == "anthropic":
        return await _probe_anthropic(req.api_key)
    if req.provider == "huggingface":
        return await _probe_huggingface(req.api_key)
    if req.provider == "ollama":
        return await _probe_ollama(req.base_url)
    if req.provider == "github":
        return await _probe_github(req.api_key)

    # FastAPI's Literal validation already rejects unknown providers,
    # so this is defensive for future additions.
    raise HTTPException(
        status_code=400, detail=f"unsupported provider {req.provider}"
    )


async def _probe_openai(api_key: Optional[str]) -> CredentialValidateResponse:
    if not api_key:
        return CredentialValidateResponse(
            provider="openai", valid=False, detail="api_key is required"
        )
    url = "https://api.openai.com/v1/models"
    try:
        async with httpx.AsyncClient(timeout=_VALIDATION_TIMEOUT_SECS) as client:
            resp = await client.get(
                url, headers={"Authorization": f"Bearer {api_key}"}
            )
    except httpx.HTTPError as exc:
        return CredentialValidateResponse(
            provider="openai",
            valid=False,
            detail=f"network error: {exc}",
            probed_url=url,
        )
    if resp.status_code == 200:
        return CredentialValidateResponse(
            provider="openai",
            valid=True,
            detail="ok",
            probed_url=url,
        )
    if resp.status_code == 401:
        return CredentialValidateResponse(
            provider="openai",
            valid=False,
            detail="invalid api_key (401)",
            probed_url=url,
        )
    return CredentialValidateResponse(
        provider="openai",
        valid=False,
        detail=f"unexpected status {resp.status_code}",
        probed_url=url,
    )


async def _probe_anthropic(
    api_key: Optional[str],
) -> CredentialValidateResponse:
    if not api_key:
        return CredentialValidateResponse(
            provider="anthropic", valid=False, detail="api_key is required"
        )
    # Anthropic has no dedicated /models listing that is cheap. We send
    # a minimal messages request with max_tokens=1 and a trivial body.
    url = "https://api.anthropic.com/v1/messages"
    body = {
        "model": "claude-3-5-haiku-latest",
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "hi"}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=_VALIDATION_TIMEOUT_SECS) as client:
            resp = await client.post(url, headers=headers, json=body)
    except httpx.HTTPError as exc:
        return CredentialValidateResponse(
            provider="anthropic",
            valid=False,
            detail=f"network error: {exc}",
            probed_url=url,
        )
    # 200 OK (accepted the call) or even 400 with a specific "you have
    # quota but the request is malformed" means the key itself works.
    if resp.status_code == 200:
        return CredentialValidateResponse(
            provider="anthropic",
            valid=True,
            detail="ok",
            probed_url=url,
        )
    if resp.status_code == 401:
        return CredentialValidateResponse(
            provider="anthropic",
            valid=False,
            detail="invalid api_key (401)",
            probed_url=url,
        )
    if resp.status_code in (402, 403, 429):
        # Key is valid but the request cannot be served. Treat as
        # authenticated: the user knows about the billing / rate
        # condition and can resolve it separately.
        return CredentialValidateResponse(
            provider="anthropic",
            valid=True,
            detail=f"key authenticated; provider responded {resp.status_code}",
            probed_url=url,
        )
    return CredentialValidateResponse(
        provider="anthropic",
        valid=False,
        detail=f"unexpected status {resp.status_code}",
        probed_url=url,
    )


async def _probe_huggingface(
    api_key: Optional[str],
) -> CredentialValidateResponse:
    if not api_key:
        return CredentialValidateResponse(
            provider="huggingface", valid=False, detail="api_key is required"
        )
    url = "https://huggingface.co/api/whoami-v2"
    try:
        async with httpx.AsyncClient(timeout=_VALIDATION_TIMEOUT_SECS) as client:
            resp = await client.get(
                url, headers={"Authorization": f"Bearer {api_key}"}
            )
    except httpx.HTTPError as exc:
        return CredentialValidateResponse(
            provider="huggingface",
            valid=False,
            detail=f"network error: {exc}",
            probed_url=url,
        )
    if resp.status_code == 200:
        try:
            name = resp.json().get("name") or "anonymous"
        except ValueError:
            name = "unknown"
        return CredentialValidateResponse(
            provider="huggingface",
            valid=True,
            detail=f"authenticated as {name}",
            probed_url=url,
        )
    if resp.status_code == 401:
        return CredentialValidateResponse(
            provider="huggingface",
            valid=False,
            detail="invalid api_key (401)",
            probed_url=url,
        )
    return CredentialValidateResponse(
        provider="huggingface",
        valid=False,
        detail=f"unexpected status {resp.status_code}",
        probed_url=url,
    )


async def _probe_ollama(
    base_url: Optional[str],
) -> CredentialValidateResponse:
    # Ollama uses no API key; we probe /api/tags as a cheap liveness check.
    base = (base_url or "http://localhost:11434").rstrip("/")
    url = f"{base}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=_VALIDATION_TIMEOUT_SECS) as client:
            resp = await client.get(url)
    except httpx.HTTPError as exc:
        return CredentialValidateResponse(
            provider="ollama",
            valid=False,
            detail=f"ollama not reachable at {base}: {exc}",
            probed_url=url,
        )
    if resp.status_code == 200:
        try:
            data = resp.json()
            model_count = len(data.get("models") or [])
        except ValueError:
            model_count = 0
        return CredentialValidateResponse(
            provider="ollama",
            valid=True,
            detail=f"ollama up, {model_count} local models",
            probed_url=url,
        )
    return CredentialValidateResponse(
        provider="ollama",
        valid=False,
        detail=f"ollama returned {resp.status_code}",
        probed_url=url,
    )


async def _probe_github(api_key: Optional[str]) -> CredentialValidateResponse:
    # GitHub auth is optional; if no key is supplied we just check the
    # anonymous rate-limit endpoint to confirm general connectivity.
    url = "https://api.github.com/user" if api_key else "https://api.github.com/rate_limit"
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        async with httpx.AsyncClient(timeout=_VALIDATION_TIMEOUT_SECS) as client:
            resp = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        return CredentialValidateResponse(
            provider="github",
            valid=False,
            detail=f"network error: {exc}",
            probed_url=url,
        )
    if api_key and resp.status_code == 200:
        try:
            login = resp.json().get("login") or "authenticated"
        except ValueError:
            login = "authenticated"
        return CredentialValidateResponse(
            provider="github",
            valid=True,
            detail=f"authenticated as {login}",
            probed_url=url,
        )
    if not api_key and resp.status_code == 200:
        return CredentialValidateResponse(
            provider="github",
            valid=True,
            detail="anonymous rate limit reachable (no token supplied)",
            probed_url=url,
        )
    if resp.status_code == 401:
        return CredentialValidateResponse(
            provider="github",
            valid=False,
            detail="invalid api_key (401)",
            probed_url=url,
        )
    return CredentialValidateResponse(
        provider="github",
        valid=False,
        detail=f"unexpected status {resp.status_code}",
        probed_url=url,
    )


@app.get("/oobe")
async def oobe_index() -> FileResponse:
    index_path = OOBE_DIST / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=503, detail="OOBE UI not built")
    return FileResponse(index_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("oobe_service:app", host="0.0.0.0", port=8099, reload=False)
