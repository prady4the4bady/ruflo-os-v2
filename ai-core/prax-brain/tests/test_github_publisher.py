from __future__ import annotations
import pytest
from pathlib import Path
import tempfile
from prav.github_publisher import GitHubPublisher

def test_create_repo_no_token():
    gp = GitHubPublisher(token="")
    result = gp.create_repo("test-repo", "Test")
    assert result is None

def test_push_no_repo():
    gp = GitHubPublisher(token="test")
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "test"
        p.mkdir()
        result = gp.push_project(p)
        assert not result
