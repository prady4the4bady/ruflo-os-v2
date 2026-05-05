from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas import ChatResponse


def test_session_crud_via_api(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LUMYN_CHROMA_PATH", str(tmp_path / "chroma"))
    app = create_app(start_scheduler=False)

    async def fake_run(*, user_message, session_context, retrieved_memories, prior_history):
        await asyncio.sleep(0)
        return ChatResponse(
            session_id="",
            answer=f"echo: {user_message}",
            status="completed",
            trace=[],
        )

    app.state.react.run = fake_run

    with TestClient(app) as client:
        r0 = client.get("/sessions")
        assert r0.status_code == 200
        assert r0.json()["sessions"] == []

        r1 = client.post("/chat", json={"session_id": "s1", "message": "hi"})
        assert r1.status_code == 200
        assert r1.json()["session_id"] == "s1"

        r2 = client.get("/sessions")
        assert r2.status_code == 200
        assert len(r2.json()["sessions"]) == 1
        assert r2.json()["sessions"][0]["session_id"] == "s1"

        r3 = client.delete("/sessions/s1")
        assert r3.status_code == 200
        assert r3.json()["deleted"] is True

        r4 = client.delete("/sessions/s1")
        assert r4.status_code == 404
