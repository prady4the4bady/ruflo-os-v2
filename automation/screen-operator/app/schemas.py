from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


ActionType = Literal["click", "type", "screenshot", "key", "open_app"]


class ActionRequest(BaseModel):
    type: ActionType
    x: Optional[int] = None
    y: Optional[int] = None
    text: Optional[str] = None
    keys: Optional[List[str]] = None
    app: Optional[str] = None

    @model_validator(mode="after")
    def validate_for_action(self) -> "ActionRequest":
        if self.type == "click":
            if self.x is None or self.y is None:
                raise ValueError("click requires x and y")
        elif self.type == "type":
            if not self.text:
                raise ValueError("type requires text")
        elif self.type == "key":
            if not self.keys:
                raise ValueError("key requires keys")
        elif self.type == "open_app" and not self.app:
            raise ValueError("open_app requires app")
        return self


class ActionResponse(BaseModel):
    success: bool
    action: str
    message: str = ""
    screenshot_base64: Optional[str] = None


class StatusResponse(BaseModel):
    display_server: Literal["wayland", "x11", "none"]
    available_tools: dict[str, bool]
    last_actions: list[dict] = Field(default_factory=list)
