from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


_ARCH_TOKENS = ["llama", "mistral", "mixtral", "qwen", "phi", "gemma", "falcon", "yi", "deepseek"]


@dataclass
class ModelMetadata:
    model_id: str
    architecture: str
    context_length: int
    quantization: str
    size_bytes: int
    ram_estimate_gb: float


def _normalize_model_id(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._:-]+", "-", text.strip().lower()).strip("-")
    return cleaned[:90] if cleaned else "model"


def _extract_quantization(name: str) -> str:
    match = re.search(r"(Q\d(?:_K)?(?:_[MSL])?)", name, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return "unknown"


def _extract_architecture(repo: str | None, file_name: str) -> str:
    haystack = f"{repo or ''} {file_name}".lower()
    for token in _ARCH_TOKENS:
        if token in haystack:
            return token
    return "unknown"


def _extract_context_length(repo: str | None, file_name: str) -> int:
    haystack = f"{repo or ''} {file_name}".lower()
    for marker in ["128k", "64k", "32k", "16k", "8k", "4k"]:
        if marker in haystack:
            return int(marker.replace("k", "")) * 1024
    return 4096


def estimate_ram_gb(size_bytes: int, quantization: str) -> float:
    overhead = 1.30
    if quantization.startswith("Q8"):
        overhead = 1.45
    elif quantization.startswith("Q2"):
        overhead = 1.20

    gb = (size_bytes * overhead) / (1024**3)
    return round(gb, 2)


def extract_metadata(file_path: Path, repo_hint: str | None = None) -> ModelMetadata:
    size = file_path.stat().st_size
    quant = _extract_quantization(file_path.name)
    arch = _extract_architecture(repo_hint, file_path.name)
    ctx = _extract_context_length(repo_hint, file_path.name)

    base_id = _normalize_model_id(file_path.stem)
    model_id = f"local-{base_id}"

    return ModelMetadata(
        model_id=model_id,
        architecture=arch,
        context_length=ctx,
        quantization=quant,
        size_bytes=size,
        ram_estimate_gb=estimate_ram_gb(size, quant),
    )
