from pathlib import Path

import yaml

from prady_models.registry import RegistryEntry, RegistryStore


def test_registry_add_and_remove(tmp_path: Path):
    registry_path = tmp_path / "model-registry.yaml"
    routing_path = tmp_path / "routing-policy.yaml"

    registry_path.write_text("models: []\n", encoding="utf-8")
    routing_path.write_text("mode: local-first\nfallback_order: [openai, anthropic]\n", encoding="utf-8")

    store = RegistryStore(registry_path, routing_path)

    entry = RegistryEntry(
        id="local-test",
        provider="ollama",
        capabilities=["chat"],
        privacy_level="private",
        latency_profile="medium",
        file_path="/tmp/local-test.gguf",
        sha256="abc",
        architecture="mistral",
        context_length=4096,
        quantization="Q4_K_M",
        ram_estimate_gb=4.2,
        status="installed",
    )

    store.add_model(entry)
    models = store.list_models()
    assert len(models) == 1
    assert models[0]["id"] == "local-test"

    removed = store.remove_model("local-test")
    assert removed is not None
    assert removed["id"] == "local-test"
    assert store.list_models() == []


def test_set_default_writes_routing_policy(tmp_path: Path):
    registry_path = tmp_path / "model-registry.yaml"
    routing_path = tmp_path / "routing-policy.yaml"

    registry_path.write_text("models: []\n", encoding="utf-8")
    routing_path.write_text("mode: local-first\nfallback_order: [openai]\n", encoding="utf-8")

    store = RegistryStore(registry_path, routing_path)
    store.set_default("local-test", "chat")

    payload = yaml.safe_load(routing_path.read_text(encoding="utf-8"))
    assert payload["default_models"]["chat"] == "local-test"
