from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def _run_ollama(model_id: str) -> tuple[bool, str]:
    if shutil.which("ollama") is None:
        return False, "ollama not found"

    proc = subprocess.run(
        ["ollama", "run", model_id, "hello"],
        capture_output=True,
        text=True,
        timeout=40,
        check=False,
    )
    if proc.returncode == 0:
        return True, "warmup via ollama succeeded"
    return False, (proc.stderr or proc.stdout or "ollama warmup failed").strip()


def _create_ollama_model(model_id: str, file_path: Path) -> tuple[bool, str]:
    if shutil.which("ollama") is None:
        return False, "ollama not found"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".modelfile", delete=False) as tmp:
        tmp.write(f"FROM {file_path}\n")
        modelfile = tmp.name

    try:
        proc = subprocess.run(
            ["ollama", "create", model_id, "-f", modelfile],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if proc.returncode == 0:
            return True, "created model in ollama"
        return False, (proc.stderr or proc.stdout or "ollama create failed").strip()
    finally:
        Path(modelfile).unlink(missing_ok=True)


def _run_llama_cpp(file_path: Path) -> tuple[bool, str]:
    try:
        from llama_cpp import Llama  # type: ignore

        llm = Llama(model_path=str(file_path), n_ctx=256, verbose=False)
        out = llm("hello", max_tokens=8)
        text = str(out.get("choices", [{}])[0].get("text", "")).strip()
        if text:
            return True, "warmup via llama-cpp-python succeeded"
        return False, "llama-cpp returned empty completion"
    except Exception as exc:
        return False, f"llama-cpp warmup failed: {exc}"


def run_warmup(model_id: str, file_path: Path) -> tuple[bool, str]:
    ok_create, msg_create = _create_ollama_model(model_id, file_path)
    if ok_create:
        ok_run, msg_run = _run_ollama(model_id)
        if ok_run:
            return True, msg_run

    ok_llama, msg_llama = _run_llama_cpp(file_path)
    if ok_llama:
        return True, msg_llama

    return False, f"warmup failed ({msg_create}); fallback: {msg_llama}"


def rollback_warmup(model_id: str) -> None:
    if shutil.which("ollama") is None:
        return
    subprocess.run(["ollama", "rm", model_id], capture_output=True, text=True, timeout=20, check=False)
