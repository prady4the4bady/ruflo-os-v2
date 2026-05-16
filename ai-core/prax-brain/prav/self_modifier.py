"""Self-modifying code engine — reads, patches, tests, and commits its own source."""
from __future__ import annotations

import ast
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_URL = os.getenv("MODEL_GATEWAY_URL", "http://model-gateway:11430")


class SelfModifier:
    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or REPO_ROOT

    def propose_patch(self, module_path: str) -> str | None:
        full_path = self.repo_root / module_path
        if not full_path.exists():
            logger.warning("Module not found: %s", module_path)
            return None
        source = full_path.read_text(encoding="utf-8")
        try:
            ast.parse(source)
        except SyntaxError as e:
            logger.warning("Syntax error in %s: %s", module_path, e)
            return None
        patch = self._llm_generate_patch(module_path, source)
        if patch and self._validate_patch_syntax(patch):
            return patch
        return None

    def apply_and_test(self, patch: str, module_path: str) -> bool:
        full_path = self.repo_root / module_path
        backup = full_path.read_text(encoding="utf-8")
        try:
            full_path.write_text(patch, encoding="utf-8")
            if self._run_tests(module_path):
                self._commit(module_path)
                return True
            full_path.write_text(backup, encoding="utf-8")
            return False
        except Exception as e:
            logger.error("Apply failed: %s", e)
            full_path.write_text(backup, encoding="utf-8")
            return False

    def rollback(self, module_path: str) -> bool:
        result = subprocess.run(
            ["git", "checkout", "--", module_path],
            capture_output=True, text=True, cwd=self.repo_root,
        )
        return result.returncode == 0

    def _validate_patch_syntax(self, patch: str) -> bool:
        try:
            ast.parse(patch)
            return True
        except SyntaxError:
            return False

    def _run_tests(self, module_path: str) -> bool:
        test_path = self._infer_test_path(module_path)
        if not test_path:
            return True
        result = subprocess.run(
            ["python", "-m", "pytest", str(test_path), "-q", "--tb=short"],
            capture_output=True, text=True, cwd=self.repo_root,
        )
        return result.returncode == 0

    def _commit(self, module_path: str) -> None:
        subprocess.run(
            ["git", "add", module_path], capture_output=True, cwd=self.repo_root,
        )
        subprocess.run(
            ["git", "commit", "-m", f"chore(prax): autonomous self-modification [skip ci]"],
            capture_output=True, cwd=self.repo_root,
        )

    def _infer_test_path(self, module_path: str) -> Path | None:
        p = Path(module_path)
        test_candidates = [
            p.parent / "tests" / f"test_{p.stem}.py",
            self.repo_root / "tests" / f"test_{p.stem}.py",
        ]
        for tc in test_candidates:
            if tc.exists():
                return tc
        return None

    def _llm_generate_patch(self, module_path: str, source: str) -> str | None:
        return source  # placeholder — real LLM integration deferred
