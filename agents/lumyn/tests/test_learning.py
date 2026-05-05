from datetime import datetime, timezone

from app.learning import build_reflection_prompt, is_failed_session
from app.schemas import SessionRecord, SessionTurn, ToolTrace


def _session(status: str, user: str = "hello", error: str | None = None) -> SessionRecord:
    trace = []
    if error:
        trace = [ToolTrace(iteration=1, thought="x", error=error)]
    turn = SessionTurn(user=user, assistant="answer", status=status, trace=trace)
    return SessionRecord(
        session_id="abc",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        turns=[turn],
    )


def test_is_failed_session_detects_status_and_feedback() -> None:
    assert is_failed_session(_session("max_iterations"))
    assert is_failed_session(_session("completed", user="that was wrong"))
    assert is_failed_session(_session("completed", error="tool failed"))
    assert not is_failed_session(_session("completed"))


def test_reflection_prompt_contains_failed_session_details() -> None:
    prompt = build_reflection_prompt([_session("error", user="do thing", error="boom")])
    assert "Failed sessions in last 24h" in prompt
    assert "tool failed" not in prompt
    assert "boom" in prompt
    assert "<|im_start|>system" in prompt
