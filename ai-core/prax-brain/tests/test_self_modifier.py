from __future__ import annotations
import pytest
from prav.self_modifier import SelfModifier

def test_propose_patch_nonexistent_module():
    sm = SelfModifier()
    assert sm.propose_patch("nonexistent.py") is None

def test_validate_patch_syntax_valid():
    sm = SelfModifier()
    assert sm._validate_patch_syntax("x = 1")

def test_validate_patch_syntax_invalid():
    sm = SelfModifier()
    assert not sm._validate_patch_syntax("x = ")

def test_propose_patch_self():
    sm = SelfModifier()
    result = sm.propose_patch("ai-core/prax-brain/prav/__init__.py")
    assert result is not None
