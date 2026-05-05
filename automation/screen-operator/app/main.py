from pathlib import Path
from typing import Any
import os

from fastapi import FastAPI, HTTPException

from .platform import ActionExecutor
from .rate_limiter import RateLimiter
from .safety_log import ActionLogger
from .schemas import ActionRequest, ActionResponse, StatusResponse


def create_app(
    executor: ActionExecutor | None = None,
    logger: ActionLogger | None = None,
    limiter: RateLimiter | None = None,
) -> FastAPI:
    app = FastAPI(title="screen-operator", version="0.1.0")

    action_executor = executor or ActionExecutor()
    log_path = Path(os.getenv("ACTIONS_LOG_PATH", "logs/actions.jsonl"))
    action_logger = logger or ActionLogger(log_path)
    rate_limiter = limiter or RateLimiter(max_actions=10, per_seconds=1.0)

    @app.get("/status")
    async def status() -> StatusResponse:
        return StatusResponse(
            display_server=action_executor.display_server,  # type: ignore[arg-type]
            available_tools=action_executor.available_tools,
            last_actions=action_logger.last_actions(),
        )

    @app.post(
        "/action",
        responses={
            400: {"description": "Action execution failed"},
            429: {"description": "Rate limit exceeded"},
        },
    )
    async def action(req: ActionRequest) -> ActionResponse:
        if not rate_limiter.allow():
            raise HTTPException(status_code=429, detail="rate limit exceeded (max 10 actions/second)")

        payload = req.model_dump(exclude_none=True)
        result = action_executor.execute(req.type, payload)
        success = bool(result.get("success", False))
        message = str(result.get("message", ""))

        params_for_log: dict[str, Any] = {k: v for k, v in payload.items() if k != "type"}
        action_logger.log(req.type, params_for_log, success, message)

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return ActionResponse(
            success=True,
            action=req.type,
            message=message,
            screenshot_base64=result.get("screenshot_base64"),
        )

    return app


app = create_app()
