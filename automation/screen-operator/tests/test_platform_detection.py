from app.platform import detect_display_server


def test_detect_wayland_when_wayland_display_set():
    server = detect_display_server({"WAYLAND_DISPLAY": "wayland-0"})
    assert server == "wayland"


def test_detect_x11_when_display_set():
    server = detect_display_server({"DISPLAY": ":0"})
    assert server == "x11"


def test_detect_none_when_no_display_env_present():
    server = detect_display_server({})
    assert server == "none"
