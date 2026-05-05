from pathlib import Path

from prady_models.config import ManagerPaths
from prady_models.download import DownloadSpec
from prady_models.logger import ActionLogger
from prady_models.manager import ModelManager, ModelManagerError
from prady_models.registry import RegistryStore


class FakeDownloader:
    def __init__(self, target_path: Path):
        self._target = target_path

    def resolve_hf(self, repo: str, file_name: str):
        return DownloadSpec(
            source_type="huggingface",
            url="https://example.com/model.gguf",
            file_name=file_name,
            expected_sha256=None,
            repo_hint=repo,
        )

    def resolve_github(self, url: str, expected_sha256=None):
        return DownloadSpec(
            source_type="github",
            url=url,
            file_name="model.gguf",
            expected_sha256=expected_sha256,
            repo_hint=None,
        )

    def download_file(self, spec: DownloadSpec, target_dir: Path):
        target_dir.mkdir(parents=True, exist_ok=True)
        self._target.write_bytes(b"hello")
        return self._target, "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_rollback_on_warmup_failure(tmp_path: Path):
    registry = tmp_path / "model-registry.yaml"
    routing = tmp_path / "routing-policy.yaml"
    model_store = tmp_path / "models"
    model_file = model_store / "model.gguf"

    registry.write_text("models: []\n", encoding="utf-8")
    routing.write_text("mode: local-first\nfallback_order: [openai]\n", encoding="utf-8")

    paths = ManagerPaths(
        project_root=tmp_path,
        model_store=model_store,
        registry_yaml=registry,
        routing_policy_yaml=routing,
        log_jsonl=tmp_path / "logs" / "model-manager.jsonl",
    )

    rollback_calls = []

    def fake_warmup(model_id: str, file_path: Path):
        return False, "boom"

    def fake_rollback(model_id: str):
        rollback_calls.append(model_id)

    manager = ModelManager(
        paths=paths,
        downloader=FakeDownloader(model_file),
        registry=RegistryStore(registry, routing),
        logger=ActionLogger(paths.log_jsonl),
        warmup_fn=fake_warmup,
        rollback_warmup_fn=fake_rollback,
    )

    try:
        manager.add_from_hf("org/repo", "model.gguf")
        assert False, "expected warmup failure"
    except ModelManagerError:
        pass

    assert manager.list_models() == []
    assert not model_file.exists()
    assert len(rollback_calls) == 1
