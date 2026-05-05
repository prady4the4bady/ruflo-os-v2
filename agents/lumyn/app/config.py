from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class LumynConfig:
    max_iterations: int
    model_preference: str
    auto_approve_safe_actions: bool
    memory_enabled: bool
    learning_enabled: bool
    model_gateway_url: str
    workflow_engine_url: str
    screen_agent_url: str
    listen_host: str
    listen_port: int
    chroma_path: Path
    learnings_file: Path


def load_config(base_dir: Path) -> LumynConfig:
    config_path = base_dir / "config" / "lumyn-config.yaml"
    raw: dict[str, Any] = {}
    if config_path.exists():
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    return LumynConfig(
        max_iterations=int(raw.get("max_iterations", 10)),
        model_preference=str(raw.get("model_preference", "local-first")),
        auto_approve_safe_actions=bool(raw.get("auto_approve_safe_actions", True)),
        memory_enabled=bool(raw.get("memory_enabled", True)),
        learning_enabled=bool(raw.get("learning_enabled", True)),
        model_gateway_url=os.getenv("MODEL_GATEWAY_URL", "http://localhost:11430"),
        workflow_engine_url=os.getenv("WORKFLOW_ENGINE_URL", "http://localhost:8001"),
        screen_agent_url=os.getenv("SCREEN_AGENT_URL", "http://localhost:11433"),
        listen_host=os.getenv("LUMYN_HOST", "0.0.0.0"),
        listen_port=int(os.getenv("LUMYN_PORT", "11436")),
        chroma_path=Path(os.getenv("LUMYN_CHROMA_PATH", str(base_dir / "data" / "chroma"))),
        learnings_file=Path(os.getenv("LUMYN_LEARNINGS_FILE", str(base_dir / "config" / "agent-learnings.jsonl"))),
    )
