"""Tests for ModelRegistry."""

from __future__ import annotations

import pytest

from app.registry import ModelRegistry


@pytest.fixture()
def reg(config_dir):  # config_dir writes model-registry.yaml to tmp_path
    return ModelRegistry()


def test_lookup_existing_model(reg: ModelRegistry):
    entry = reg.lookup("llama3.2:3b")
    assert entry is not None
    assert entry.id == "llama3.2:3b"
    assert entry.provider == "ollama"


def test_lookup_missing_returns_none(reg: ModelRegistry):
    entry = reg.lookup("nonexistent-model-xyz")
    assert entry is None


def test_all_returns_all(reg: ModelRegistry):
    models = reg.all()
    assert len(models) == 3  # matches conftest MODEL_REGISTRY_DATA
    ids = [m.id for m in models]
    assert "llama3.2:3b" in ids
    assert "gpt-4o" in ids
    assert "claude-3-5-sonnet-20241022" in ids


def test_by_provider_filters(reg: ModelRegistry):
    ollama_models = reg.by_provider("ollama")
    assert len(ollama_models) == 1
    assert ollama_models[0].id == "llama3.2:3b"


def test_by_provider_unknown_returns_empty(reg: ModelRegistry):
    models = reg.by_provider("banana")
    assert models == []


def test_model_has_capabilities(reg: ModelRegistry):
    entry = reg.lookup("llama3.2:3b")
    assert entry is not None
    assert "chat" in entry.capabilities


def test_model_privacy_level(reg: ModelRegistry):
    ollama_entry = reg.lookup("llama3.2:3b")
    assert ollama_entry is not None
    assert ollama_entry.privacy_level == "private"

    cloud_entry = reg.lookup("gpt-4o")
    assert cloud_entry is not None
    assert cloud_entry.privacy_level == "cloud"


def test_len(reg: ModelRegistry):
    assert len(reg) == 3
