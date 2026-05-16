from __future__ import annotations
import pytest
from prav.researcher import Researcher, Idea

def test_score_idea():
    r = Researcher()
    idea = Idea(title="A novel AI system for healthcare", source="test", url="https://example.com")
    result = r.score_idea(idea)
    assert result.score > 0

def test_score_impact_health():
    r = Researcher()
    idea = Idea(title="healthcare platform", source="test", url="https://example.com")
    result = r.score_idea(idea)
    assert result.score > 0.3

def test_get_top_proposals_empty():
    r = Researcher()
    top = r.get_top_proposals(n=3)
    assert isinstance(top, list)
