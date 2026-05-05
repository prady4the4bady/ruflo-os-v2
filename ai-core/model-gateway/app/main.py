"""FastAPI application – Vyrex model gateway.

Exposed routes
──────────────
  POST /v1/chat/completions   OpenAI-compatible chat
  POST /v1/completions        OpenAI-compatible text completion
  GET  /v1/models             List all registered models
  GET  /healthz               Health / liveness check
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.audit import get_audit_logger, reset_audit_logger
from app.config import load_routing_policy, reset_config_cache
from app.gateway import GatewayError, ModelGateway
from app.middleware import CorrelationIDMiddleware
from app.policy import RoutingPolicyEngine, reset_policy_engine
from app.registry import ModelRegistry, reset_registry
from app.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    CompletionRequest,
    CompletionResponse,
    ErrorDetail,
    ErrorResponse,
    ModelInfo,
    ModelsResponse,
)

# Load .env if present (development convenience)
load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application-level singletons (created once at startup)
# ---------------------------------------------------------------------------

_gateway: ModelGateway | None = None
_registry: ModelRegistry | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    global _gateway, _registry

    # --- startup ---
    logger.info("model-gateway starting up")
    policy_cfg = load_routing_policy()
    audit = get_audit_logger()
    engine = RoutingPolicyEngine(policy_cfg)
    _gateway = ModelGateway(policy_cfg=policy_cfg, policy_engine=engine, audit=audit)
    _registry = ModelRegistry()
    logger.info(
        "routing mode=%s, registered models=%d",
        policy_cfg.mode,
        len(_registry),
    )
    yield

    # --- shutdown ---
    logger.info("model-gateway shutting down")
    reset_config_cache()
    reset_policy_engine()
    reset_registry()
    reset_audit_logger()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Vyrex Model Gateway",
    description=(
        "OpenAI-compatible inference gateway with local-first routing. "
        "Routes requests to Ollama (local) or cloud providers based on policy."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(CorrelationIDMiddleware)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(GatewayError)
async def gateway_error_handler(request: Request, exc: GatewayError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorDetail(message=str(exc))
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error [correlation_id=%s]", _cid(request))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error=ErrorDetail(message="Internal server error", type="internal_error")
        ).model_dump(),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict[str, Any]:
    """Liveness probe."""
    return {"status": "ok", "ts": int(time.time())}


@app.get("/v1/models", response_model=ModelsResponse, tags=["models"])
async def list_models() -> ModelsResponse:
    """Return all models known to the registry."""
    assert _registry is not None, "Registry not initialised"
    provider_map = {
        "ollama": "prady",
        "openai": "openai",
        "anthropic": "anthropic",
    }
    data = [
        ModelInfo(
            id=m.id,
            owned_by=provider_map.get(m.provider, m.provider),
        )
        for m in _registry.all()
    ]
    return ModelsResponse(data=data)


@app.post(
    "/v1/chat/completions",
    response_model=ChatCompletionResponse,
    tags=["chat"],
)
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
) -> ChatCompletionResponse:
    """OpenAI-compatible chat completion endpoint."""
    assert _gateway is not None, "Gateway not initialised"
    return await _gateway.chat_completion(body, correlation_id=_cid(request))


@app.post(
    "/v1/completions",
    response_model=CompletionResponse,
    tags=["completions"],
)
async def completions(
    request: Request,
    body: CompletionRequest,
) -> CompletionResponse:
    """OpenAI-compatible text completion endpoint (converted to chat internally)."""
    assert _gateway is not None, "Gateway not initialised"
    return await _gateway.completion(body, correlation_id=_cid(request))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "unknown")
