from __future__ import annotations
import pytest
from prav.mind_rewriter import MindRewriter

def test_analyze_performance(mock_prax_dir):
    mr = MindRewriter(mock_prax_dir)
    perf = mr.analyze_performance()
    assert "proposal_acceptance_rate" in perf
    assert "build_success_rate" in perf

def test_evolve_creates_log(mock_prax_dir):
    mr = MindRewriter(mock_prax_dir)
    assert mr.evolve()
    assert (mock_prax_dir / "mind_evolution.log").exists()
