from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── Request models ──────────────────────────────────────────────────────────

class MouseMoveRequest(BaseModel):
    x: int = Field(..., description="Target X coordinate in screen pixels")
    y: int = Field(..., description="Target Y coordinate in screen pixels")


class MouseClickRequest(BaseModel):
    x: int = Field(..., description="Target X coordinate in screen pixels")
    y: int = Field(..., description="Target Y coordinate in screen pixels")
    button: Literal["left", "right", "double"] = Field(
        "left", description="Mouse button to click"
    )


class KeyboardTypeRequest(BaseModel):
    text: str = Field(..., description="Text string to type via keyboard")


class ScreenshotRequest(BaseModel):
    label: str = Field("screenshot", description="Label used in the saved filename")


class KeyComboRequest(BaseModel):
    keys: list[str] = Field(
        ...,
        description="Ordered list of keys forming the combo (e.g. ['ctrl', 'c'])",
        min_length=1,
    )


class DescribeScreenRequest(BaseModel):
    prompt: str = Field(
        ..., description="Natural-language question about the current screen state"
    )


# ── Response models ──────────────────────────────────────────────────────────

class ActionResponse(BaseModel):
    success: bool
    message: str
    path: str | None = None  # populated for screenshot action


class CursorPosResponse(BaseModel):
    x: int
    y: int


class DescribeScreenResponse(BaseModel):
    description: str
    screenshot_path: str
