from __future__ import annotations

from pathlib import Path
from typing import Any, Annotated

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
import uvicorn

from prady_models.config import default_paths
from prady_models.manager import ModelManager, ModelManagerError


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def create_app() -> FastAPI:
    app = FastAPI(title="nemos-model-manager")
    manager = ModelManager(default_paths())

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        status = manager.get_status()
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "models": status["models"],
                "routing": status["routing_policy"],
            },
        )

    @app.get("/api/models")
    async def api_models() -> dict[str, Any]:
        return manager.get_status()

    @app.post("/api/install-hf")
    async def api_install_hf(
        hf_repo: Annotated[str, Form(...)],
        file_name: Annotated[str, Form(...)],
        sha256: Annotated[str, Form()] = "",
    ) -> JSONResponse:
        try:
            result = manager.add_from_hf(hf_repo, file_name, sha256 or None)
            return JSONResponse({"ok": True, "result": result.__dict__})
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @app.post("/api/install-github")
    async def api_install_github(
        github_url: Annotated[str, Form(...)],
        sha256: Annotated[str, Form()] = "",
    ) -> JSONResponse:
        try:
            result = manager.add_from_github(github_url, sha256 or None)
            return JSONResponse({"ok": True, "result": result.__dict__})
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @app.post("/api/remove/{model_id}")
    async def api_remove(model_id: str) -> JSONResponse:
        try:
            removed = manager.remove_model(model_id)
            return JSONResponse({"ok": True, "removed": removed})
        except ModelManagerError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)

    @app.post(
        "/api/set-default",
        responses={400: {"description": "Invalid capability or unsupported model capability"}},
    )
    async def api_set_default(
        model_id: Annotated[str, Form(...)],
        capability: Annotated[str, Form(...)],
    ) -> JSONResponse:
        mapping = {"coding": "code", "chat": "chat", "vision": "vision"}
        if capability not in mapping:
            raise HTTPException(status_code=400, detail="capability must be coding|chat|vision")
        try:
            manager.set_default(model_id, mapping[capability])
            return JSONResponse({"ok": True})
        except ModelManagerError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @app.post("/api/routing-policy")
    async def api_routing_policy(
        mode: Annotated[str, Form(...)],
        fallback_order: Annotated[str, Form(...)],
    ) -> JSONResponse:
        providers = [p.strip() for p in fallback_order.split(",") if p.strip()]
        policy = manager.update_routing_policy(mode=mode, fallback_order=providers)
        return JSONResponse({"ok": True, "routing_policy": policy})

    return app


def run_web(host: str = "127.0.0.1", port: int = 11432) -> None:
    uvicorn.run(create_app(), host=host, port=port)
