def test_status_exposes_display_tools_and_recent_actions(app_client):
    client, _, _ = app_client

    client.post("/action", json={"type": "type", "text": "hello"})
    client.post("/action", json={"type": "key", "keys": ["ctrl", "c"]})

    response = client.get("/status")
    assert response.status_code == 200

    body = response.json()
    assert body["display_server"] == "x11"
    assert "xdotool" in body["available_tools"]
    assert len(body["last_actions"]) == 2
    assert body["last_actions"][0]["type"] == "type"
    assert body["last_actions"][1]["type"] == "key"
