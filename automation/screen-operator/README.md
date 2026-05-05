# screen-operator

Python automation service exposing local REST actions for click, type, key, screenshot, and app launch.

Runs on Linux with display auto-detection:

- Wayland path: ydotool (+ ydotoold)
- X11 path: xdotool (+ python-xlib detected)
- Screenshot: grim (Wayland) or scrot fallback

## Run

```bash
pip install -r requirements-dev.txt
uvicorn app.main:app --host 127.0.0.1 --port 11431
```

## Endpoints

- `POST /action`
- `GET /status`
