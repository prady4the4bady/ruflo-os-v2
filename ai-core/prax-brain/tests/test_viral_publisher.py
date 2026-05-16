from __future__ import annotations
import pytest
from prav.viral_publisher import ViralPublisher

def test_post_all_returns_dict():
    vp = ViralPublisher()
    result = vp.post_all("test-proj", "https://github.com/test/test", "A test project")
    assert isinstance(result, dict)
    assert all(isinstance(v, bool) for v in result.values())
