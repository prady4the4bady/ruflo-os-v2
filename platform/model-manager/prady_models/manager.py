from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prady_models.config import ManagerPaths
from prady_models.download import DownloadError, DownloadSpec, Downloader
from prady_models.logger import ActionLogger
from prady_models.metadata import extract_metadata
from prady_models.registry import RegistryEntry, RegistryStore
from prady_models.warmup import rollback_warmup, run_warmup


class ModelManagerError(RuntimeError):
    pass


@dataclass
class AddResult:
    model_id: str
    file_path: str
    sha256: str
    architecture: str
    context_length: int
    quantization: str
    ram_estimate_gb: float
    status: str


class ModelManager:
    def __init__(
        self,
        paths: ManagerPaths,
        downloader: Downloader | None = None,
        registry: RegistryStore | None = None,
        logger: ActionLogger | None = None,
        warmup_fn=run_warmup,
        rollback_warmup_fn=rollback_warmup,
    ) -> None:
        self._paths = paths
        self._downloader = downloader or Downloader()
        self._registry = registry or RegistryStore(paths.registry_yaml, paths.routing_policy_yaml)
        self._logger = logger or ActionLogger(paths.log_jsonl)
        self._warmup = warmup_fn
        self._rollback_warmup = rollback_warmup_fn

    def list_models(self) -> list[dict[str, Any]]:
        models = self._registry.list_models()
        self._logger.log("list", "success", count=len(models))
        return models

    def add_from_hf(self, hf_repo: str, file_name: str, expected_sha256: str | None = None) -> AddResult:
        spec = self._downloader.resolve_hf(hf_repo, file_name)
        if expected_sha256:
            spec.expected_sha256 = expected_sha256.lower()
        return self._add_pipeline(spec)

    def add_from_github(self, github_url: str, expected_sha256: str | None = None) -> AddResult:
        spec = self._downloader.resolve_github(github_url, expected_sha256)
        return self._add_pipeline(spec)

    def _add_pipeline(self, spec: DownloadSpec) -> AddResult:
        self._logger.log("add", "started", source=spec.source_type, url=spec.url, file=spec.file_name)

        downloaded: Path | None = None
        model_id: str | None = None
        registered = False

        try:
            downloaded, actual_sha = self._downloader.download_file(spec, self._paths.model_store)
            metadata = extract_metadata(downloaded, spec.repo_hint)
            model_id = metadata.model_id

            entry = RegistryEntry(
                id=model_id,
                provider="ollama",
                capabilities=["chat", "completion", "code"],
                privacy_level="private",
                latency_profile="medium",
                file_path=str(downloaded),
                sha256=actual_sha,
                architecture=metadata.architecture,
                context_length=metadata.context_length,
                quantization=metadata.quantization,
                ram_estimate_gb=metadata.ram_estimate_gb,
                status="installed",
            )

            self._registry.add_model(entry)
            registered = True

            ok, warmup_message = self._warmup(model_id, downloaded)
            if not ok:
                raise ModelManagerError(f"Warmup failed: {warmup_message}")

            self._logger.log(
                "add",
                "success",
                model_id=model_id,
                file=str(downloaded),
                sha256=actual_sha,
                warmup=warmup_message,
            )

            return AddResult(
                model_id=model_id,
                file_path=str(downloaded),
                sha256=actual_sha,
                architecture=metadata.architecture,
                context_length=metadata.context_length,
                quantization=metadata.quantization,
                ram_estimate_gb=metadata.ram_estimate_gb,
                status="installed",
            )
        except Exception as exc:
            if registered and model_id:
                self._registry.remove_model(model_id)
            if model_id:
                self._rollback_warmup(model_id)
            if downloaded is not None and downloaded.exists():
                downloaded.unlink(missing_ok=True)

            self._logger.log("add", "failed", reason=str(exc), source=spec.source_type, file=spec.file_name)
            if isinstance(exc, (DownloadError, ModelManagerError, ValueError)):
                raise
            raise ModelManagerError(str(exc)) from exc

    def remove_model(self, model_id: str) -> dict[str, Any]:
        item = self._registry.remove_model(model_id)
        if item is None:
            self._logger.log("remove", "failed", model_id=model_id, reason="not found")
            raise ModelManagerError(f"Model not found: {model_id}")

        file_path = item.get("file_path")
        if file_path:
            path = Path(str(file_path))
            path.unlink(missing_ok=True)

        self._rollback_warmup(model_id)
        self._logger.log("remove", "success", model_id=model_id)
        return item

    def set_default(self, model_id: str, capability: str) -> None:
        model = self._registry.get_model(model_id)
        if model is None:
            self._logger.log("set-default", "failed", model_id=model_id, capability=capability, reason="not found")
            raise ModelManagerError(f"Model not found: {model_id}")

        capabilities = list(model.get("capabilities") or [])
        if capability not in capabilities:
            self._logger.log(
                "set-default",
                "failed",
                model_id=model_id,
                capability=capability,
                reason="capability not supported",
            )
            raise ModelManagerError(f"Model '{model_id}' does not support capability '{capability}'")

        self._registry.set_default(model_id, capability)
        self._logger.log("set-default", "success", model_id=model_id, capability=capability)

    def get_status(self) -> dict[str, Any]:
        models = self._registry.list_models()
        policy = self._registry.get_routing_policy()
        return {
            "models": models,
            "routing_policy": {
                "mode": policy.get("mode", "local-first"),
                "fallback_order": policy.get("fallback_order", ["openai", "anthropic"]),
                "default_models": policy.get("default_models", {}),
            },
        }

    def update_routing_policy(self, mode: str, fallback_order: list[str]) -> dict[str, Any]:
        policy = self._registry.update_routing_policy(mode, fallback_order)
        self._logger.log("routing-policy", "success", mode=mode, fallback_order=fallback_order)
        return policy
