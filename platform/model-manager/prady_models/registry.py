from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class RegistryEntry:
    id: str
    provider: str
    capabilities: list[str]
    privacy_level: str
    latency_profile: str
    file_path: str
    sha256: str
    architecture: str
    context_length: int
    quantization: str
    ram_estimate_gb: float
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "provider": self.provider,
            "capabilities": self.capabilities,
            "privacy_level": self.privacy_level,
            "latency_profile": self.latency_profile,
            "file_path": self.file_path,
            "sha256": self.sha256,
            "architecture": self.architecture,
            "context_length": self.context_length,
            "quantization": self.quantization,
            "ram_estimate_gb": self.ram_estimate_gb,
            "status": self.status,
        }


class RegistryStore:
    def __init__(self, registry_path: Path, routing_policy_path: Path) -> None:
        self._registry_path = registry_path
        self._routing_policy_path = routing_policy_path

    def _read_yaml(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

    def _write_yaml(self, path: Path, payload: dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(payload, fh, sort_keys=False)

    def list_models(self) -> list[dict[str, Any]]:
        data = self._read_yaml(self._registry_path)
        return list(data.get("models") or [])

    def get_model(self, model_id: str) -> dict[str, Any] | None:
        for item in self.list_models():
            if item.get("id") == model_id:
                return item
        return None

    def add_model(self, entry: RegistryEntry) -> None:
        data = self._read_yaml(self._registry_path)
        models = list(data.get("models") or [])

        if any(m.get("id") == entry.id for m in models):
            raise ValueError(f"Model id already exists: {entry.id}")

        models.append(entry.to_dict())
        data["models"] = models
        self._write_yaml(self._registry_path, data)

    def remove_model(self, model_id: str) -> dict[str, Any] | None:
        data = self._read_yaml(self._registry_path)
        models = list(data.get("models") or [])

        removed = None
        remaining = []
        for model in models:
            if model.get("id") == model_id:
                removed = model
            else:
                remaining.append(model)

        if removed is None:
            return None

        data["models"] = remaining
        self._write_yaml(self._registry_path, data)

        policy = self._read_yaml(self._routing_policy_path)
        defaults = policy.get("default_models") or {}
        to_remove = [cap for cap, default_id in defaults.items() if default_id == model_id]
        changed = bool(to_remove)
        for capability in to_remove:
            defaults.pop(capability, None)
        if changed:
            policy["default_models"] = defaults
            self._write_yaml(self._routing_policy_path, policy)

        return removed

    def set_default(self, model_id: str, capability: str) -> None:
        policy = self._read_yaml(self._routing_policy_path)
        defaults = dict(policy.get("default_models") or {})
        defaults[capability] = model_id
        policy["default_models"] = defaults
        self._write_yaml(self._routing_policy_path, policy)

    def get_routing_policy(self) -> dict[str, Any]:
        return self._read_yaml(self._routing_policy_path)

    def update_routing_policy(self, mode: str, fallback_order: list[str]) -> dict[str, Any]:
        policy = self._read_yaml(self._routing_policy_path)
        policy["mode"] = mode
        policy["fallback_order"] = fallback_order
        self._write_yaml(self._routing_policy_path, policy)
        return policy
