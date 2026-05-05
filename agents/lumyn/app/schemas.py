from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str
    message: str
    context: dict[str, Any] | None = None


class ExecuteRequest(BaseModel):
    goal: str
    auto_approve: bool = False


class MemorySearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=3, ge=1, le=20)


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolTrace(BaseModel):
    iteration: int
    thought: str
    action: str | None = None
    action_input: dict[str, Any] | None = None
    observation: str | None = None
    error: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    status: Literal["completed", "max_iterations", "error"]
    trace: list[ToolTrace]


class SessionSummary(BaseModel):
    session_id: str
    created_at: datetime
    updated_at: datetime
    turns: int


class SessionTurn(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user: str
    assistant: str
    status: str
    trace: list[ToolTrace] = Field(default_factory=list)


class SessionRecord(BaseModel):
    session_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    turns: list[SessionTurn] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryHit(BaseModel):
    session_id: str
    score: float
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
