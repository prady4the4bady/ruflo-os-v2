from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.rate_limiter import RateLimiter
from app.safety_log import ActionLogger


class NoopExecutor:
    display_server = "x11"
    available_tools = {
        "ydotool": False,
        "xdotool": True,
        "grim": False,
        "scrot": True,
        "python_xlib": True,
    }

    def execute(self, action_type, payload):
        return {"success": True, "message": "ok"}


def test_rate_limit_blocks_after_threshold(tmp_path: Path):
    app = create_app(
        executor=NoopExecutor(),
        logger=ActionLogger(tmp_path / "actions.jsonl"),
        limiter=RateLimiter(max_actions=1, per_seconds=60.0),
    )
    client = TestClient(app)

    first = client.post("/action", json={"type": "screenshot"})
    second = client.post("/action", json={"type": "screenshot"})

    assert first.status_code == 200
    assert second.status_code == 429
