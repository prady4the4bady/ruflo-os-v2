from __future__ import annotations
import pytest
from types import SimpleNamespace
from prav.project_builder import ProjectBuilder

def test_scaffold_creates_structure(mock_prax_dir):
    pb = ProjectBuilder(mock_prax_dir)
    proposal = SimpleNamespace(title="my-test-project", problem_statement="Test problem")
    path = pb.scaffold(proposal)
    assert (path / "src" / "main.py").exists()
    assert (path / "tests").exists()
    assert (path / "README.md").exists()

def test_scaffold_slugify():
    assert ProjectBuilder._slugify("Hello World Project") == "hello-world-project"
    assert len(ProjectBuilder._slugify("a" * 100)) <= 64
