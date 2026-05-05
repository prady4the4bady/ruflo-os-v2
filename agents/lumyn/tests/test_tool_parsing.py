from app.lumyn_format import parse_tool_call, strip_tool_call_block


def test_parse_tool_call_from_lumyn_xml_block() -> None:
    text = (
        "I should inspect the project first.\n"
        "<tool_call>{\"name\":\"read_file\",\"arguments\":{\"path\":\"README.md\"}}</tool_call>"
    )
    call = parse_tool_call(text)
    assert call is not None
    assert call.name == "read_file"
    assert call.arguments["path"] == "README.md"


def test_parse_tool_call_returns_none_when_missing() -> None:
    assert parse_tool_call("No tool call here.") is None


def test_strip_tool_call_block_removes_xml_tag() -> None:
    text = "Think. <tool_call>{\"name\":\"run_shell\",\"arguments\":{\"command\":\"pwd\"}}</tool_call>"
    stripped = strip_tool_call_block(text)
    assert "tool_call" not in stripped
    assert stripped.startswith("Think")
