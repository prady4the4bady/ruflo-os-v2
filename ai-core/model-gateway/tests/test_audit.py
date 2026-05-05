"""Tests for AuditLogger."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.audit import AuditLogger

pytestmark = pytest.mark.anyio


async def test_audit_creates_file(tmp_path: Path):
    logger = AuditLogger(log_dir=tmp_path)
    await logger.log_request(
        correlation_id="cid-1",
        endpoint="chat/completions",
        model="llama3.2:3b",
        policy_mode="local-first",
        backends_to_try=["ollama", "openai"],
    )
    assert logger.log_path.exists()


async def test_audit_request_fields(tmp_path: Path):
    logger = AuditLogger(log_dir=tmp_path)
    await logger.log_request(
        correlation_id="cid-req",
        endpoint="chat/completions",
        model="llama3.2:3b",
        policy_mode="local-first",
        backends_to_try=["ollama"],
    )
    lines = logger.log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "request"
    assert record["correlation_id"] == "cid-req"
    assert record["endpoint"] == "chat/completions"
    assert record["model"] == "llama3.2:3b"
    assert record["policy_mode"] == "local-first"
    assert record["backends_to_try"] == ["ollama"]
    assert "ts" in record


async def test_audit_response_fields(tmp_path: Path):
    logger = AuditLogger(log_dir=tmp_path)
    await logger.log_response(
        correlation_id="cid-resp",
        backend="ollama",
        success=True,
        model="llama3.2:3b",
        latency_ms=42.3,
    )
    lines = logger.log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "response"
    assert record["correlation_id"] == "cid-resp"
    assert record["backend"] == "ollama"
    assert record["success"] is True
    assert record["model"] == "llama3.2:3b"
    assert record["latency_ms"] == pytest.approx(42.3)


async def test_audit_appends_not_overwrites(tmp_path: Path):
    logger = AuditLogger(log_dir=tmp_path)
    await logger.log_request(
        correlation_id="cid-a",
        endpoint="chat/completions",
        model="m1",
        policy_mode="local-first",
        backends_to_try=["ollama"],
    )
    await logger.log_request(
        correlation_id="cid-b",
        endpoint="completions",
        model="m2",
        policy_mode="cloud-only",
        backends_to_try=["openai"],
    )
    lines = logger.log_path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["correlation_id"] == "cid-a"
    assert json.loads(lines[1])["correlation_id"] == "cid-b"


async def test_audit_failure_response(tmp_path: Path):
    logger = AuditLogger(log_dir=tmp_path)
    await logger.log_response(
        correlation_id="cid-fail",
        backend="openai",
        success=False,
        error="Connection refused",
    )
    record = json.loads(logger.log_path.read_text())
    assert record["success"] is False
    assert record["error"] == "Connection refused"
    assert "model" not in record
    assert "latency_ms" not in record


async def test_audit_concurrent_writes(tmp_path: Path):
    """Multiple concurrent appends must not interleave lines."""
    import asyncio

    logger = AuditLogger(log_dir=tmp_path)
    coros = [
        logger.log_request(
            correlation_id=f"cid-{i}",
            endpoint="chat/completions",
            model="m",
            policy_mode="local-first",
            backends_to_try=["ollama"],
        )
        for i in range(20)
    ]
    await asyncio.gather(*coros)
    lines = logger.log_path.read_text().strip().splitlines()
    assert len(lines) == 20
    # every line must be valid JSON
    for line in lines:
        record = json.loads(line)
        assert record["event"] == "request"
