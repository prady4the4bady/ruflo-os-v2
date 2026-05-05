"""Tests for the routing policy engine."""

from __future__ import annotations

import pytest

from app.policy import RoutingPolicyEngine


# ---------------------------------------------------------------------------
# local-first
# ---------------------------------------------------------------------------


def test_local_first_includes_ollama(policy_local_first):
    engine = RoutingPolicyEngine(policy_local_first)
    decision = engine.decide("llama3.2:3b")
    assert decision.allowed is True
    assert decision.backends[0] == "ollama"


def test_local_first_includes_fallbacks(policy_local_first):
    engine = RoutingPolicyEngine(policy_local_first)
    decision = engine.decide("gpt-4o")
    assert "openai" in decision.backends
    assert "anthropic" in decision.backends


def test_local_first_ordered_ollama_then_cloud(policy_local_first):
    engine = RoutingPolicyEngine(policy_local_first)
    decision = engine.decide("llama3.2:3b")
    assert decision.backends.index("ollama") < decision.backends.index("openai")


# ---------------------------------------------------------------------------
# local-only
# ---------------------------------------------------------------------------


def test_local_only_returns_only_ollama(policy_local_only):
    engine = RoutingPolicyEngine(policy_local_only)
    decision = engine.decide("llama3.2:3b")
    assert decision.allowed is True
    assert decision.backends == ["ollama"]


def test_is_local_only_true(policy_local_only):
    engine = RoutingPolicyEngine(policy_local_only)
    assert engine.is_local_only() is True


def test_is_local_only_false(policy_local_first):
    engine = RoutingPolicyEngine(policy_local_first)
    assert engine.is_local_only() is False


# ---------------------------------------------------------------------------
# cloud-only
# ---------------------------------------------------------------------------


def test_cloud_only_excludes_ollama(policy_cloud_only):
    engine = RoutingPolicyEngine(policy_cloud_only)
    decision = engine.decide("gpt-4o")
    assert "ollama" not in decision.backends


def test_cloud_only_includes_fallback_order(policy_cloud_only):
    engine = RoutingPolicyEngine(policy_cloud_only)
    decision = engine.decide("gpt-4o")
    assert decision.backends == ["openai", "anthropic"]


# ---------------------------------------------------------------------------
# invalid mode
# ---------------------------------------------------------------------------


def test_invalid_mode_not_allowed(config_dir):
    import yaml
    from app.config import RoutingPolicyConfig, reset_config_cache

    bad_data = {
        "mode": "banana",
        "local_timeout_seconds": 5,
        "providers": {
            "ollama": {"base_url": "http://localhost:11434", "timeout_seconds": 5},
        },
        "fallback_order": [],
    }
    (config_dir / "routing-policy.yaml").write_text(
        yaml.dump(bad_data), encoding="utf-8"
    )
    reset_config_cache()
    from app.config import load_routing_policy

    with pytest.raises(ValueError, match="Invalid routing mode"):
        load_routing_policy()


# ---------------------------------------------------------------------------
# ordered_backends helper
# ---------------------------------------------------------------------------


def test_ordered_backends_local_first(policy_local_first):
    engine = RoutingPolicyEngine(policy_local_first)
    backends = engine.ordered_backends()
    assert backends[0] == "ollama"


def test_ordered_backends_cloud_only(policy_cloud_only):
    engine = RoutingPolicyEngine(policy_cloud_only)
    backends = engine.ordered_backends()
    assert "ollama" not in backends
