from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ManagerPaths:
    project_root: Path
    model_store: Path
    registry_yaml: Path
    routing_policy_yaml: Path
    log_jsonl: Path


def default_paths() -> ManagerPaths:
    project_root = Path(__file__).resolve().parents[1]
    repo_root = project_root.parents[1]

    return ManagerPaths(
        project_root=project_root,
        model_store=Path.home() / ".nemos" / "models",
        registry_yaml=repo_root / "ai-core" / "model-gateway" / "config" / "model-registry.yaml",
        routing_policy_yaml=repo_root / "ai-core" / "model-gateway" / "config" / "routing-policy.yaml",
        log_jsonl=project_root / "logs" / "model-manager.jsonl",
    )
