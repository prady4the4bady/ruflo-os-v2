def test_click_routes_to_executor(app_client):
    client, executor, _ = app_client
    response = client.post("/action", json={"type": "click", "x": 400, "y": 300})

    assert response.status_code == 200
    assert executor.calls[-1][0] == "click"
    assert executor.calls[-1][1]["x"] == 400
    assert executor.calls[-1][1]["y"] == 300


def test_type_routes_to_executor(app_client):
    client, executor, _ = app_client
    response = client.post("/action", json={"type": "type", "text": "hello world"})

    assert response.status_code == 200
    assert executor.calls[-1][0] == "type"
    assert executor.calls[-1][1]["text"] == "hello world"


def test_key_routes_to_executor(app_client):
    client, executor, _ = app_client
    response = client.post("/action", json={"type": "key", "keys": ["ctrl", "c"]})

    assert response.status_code == 200
    assert executor.calls[-1][0] == "key"
    assert executor.calls[-1][1]["keys"] == ["ctrl", "c"]


def test_open_app_routes_to_executor(app_client):
    client, executor, _ = app_client
    response = client.post("/action", json={"type": "open_app", "app": "firefox"})

    assert response.status_code == 200
    assert executor.calls[-1][0] == "open_app"
    assert executor.calls[-1][1]["app"] == "firefox"


def test_screenshot_returns_base64(app_client):
    client, executor, _ = app_client
    response = client.post("/action", json={"type": "screenshot"})

    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "screenshot"
    assert data["screenshot_base64"] == "dGVzdA=="
    assert executor.calls[-1][0] == "screenshot"
