from __future__ import annotations

import json
from typing import Optional

import typer

from prady_models.config import default_paths
from prady_models.manager import ModelManager
from prady_models.web import run_web


app = typer.Typer(help="Prady model manager")


def _manager() -> ModelManager:
    return ModelManager(default_paths())


@app.command("list")
def list_models() -> None:
    manager = _manager()
    models = manager.list_models()
    typer.echo(json.dumps(models, indent=2))


@app.command("add")
def add_model(
    hf_repo: Optional[str] = typer.Option(None, "--hf-repo", help="Hugging Face repository"),
    file: Optional[str] = typer.Option(None, "--file", help="GGUF file name within HF repo"),
    github_url: Optional[str] = typer.Option(None, "--github-url", help="GitHub release URL"),
    sha256: Optional[str] = typer.Option(None, "--sha256", help="Expected SHA256 override"),
) -> None:
    manager = _manager()

    if hf_repo and file:
        result = manager.add_from_hf(hf_repo, file, sha256)
    elif github_url:
        result = manager.add_from_github(github_url, sha256)
    else:
        raise typer.BadParameter("Provide --hf-repo with --file, or --github-url")

    typer.echo(json.dumps(result.__dict__, indent=2))


@app.command("remove")
def remove_model(model_id: str) -> None:
    manager = _manager()
    removed = manager.remove_model(model_id)
    typer.echo(json.dumps(removed, indent=2))


@app.command("set-default")
def set_default(model_id: str, capability: str = typer.Option(..., "--capability")) -> None:
    if capability not in {"coding", "chat", "vision"}:
        raise typer.BadParameter("capability must be one of coding|chat|vision")

    capability_map = {"coding": "code", "chat": "chat", "vision": "vision"}
    manager = _manager()
    manager.set_default(model_id, capability_map[capability])
    typer.echo(f"Default model for {capability} set to {model_id}")


@app.command("serve")
def serve(host: str = "127.0.0.1", port: int = 11432) -> None:
    run_web(host=host, port=port)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
