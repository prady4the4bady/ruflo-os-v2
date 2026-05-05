# Prady Desktop Shell (Phase 4)

A real GTK4 desktop shell implementation for Linux, Wayland-first with X11 fallback support.

## Features

- Top bar (macOS-like menubar)
  - left: Prady logo + focused app/window name
  - center: live clock
  - right: AI status, battery, wifi, user menu
  - dark/light theme from config
- Bottom dock with auto-hide and smooth reveal animation
  - pinned apps + running-app dot indicator
  - right-click app context menu
- Spotlight-like launcher
  - toggle with `Super` key when shell has keyboard focus
  - fuzzy search over apps/files/settings + AI shortcut
  - keyboard navigation and enter-to-open
- AI task bar above dock
  - submit natural-language goals to Phase 2 orchestration engine
  - progress polling + inline approval prompts
- Notifications center
  - slide-in panel from top right
  - stacked cards including AI task events
- Layer-shell support with graceful fallback
  - if `gtk4-layer-shell` is available: anchored shell layer
  - otherwise runs as undecorated maximized standalone window

## Project layout

- `main.py`: entrypoint
- `prady_shell/app.py`: GTK app bootstrap
- `prady_shell/shell_window.py`: shell composition and overlays
- `prady_shell/widgets/`: top bar, dock, launcher, notifications, AI task bar
- `prady_shell/services/`: orchestration API, search, window/system status
- `prady_shell/config.py`: `~/.config/nemos/shell.yaml` loader/initializer

## Dependencies

System packages (example for Ubuntu/Debian):

```bash
sudo apt update
sudo apt install -y python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
  python3-psutil python3-yaml xdotool nmcli upower
```

Optional for layer-shell mode:

```bash
sudo apt install -y gir1.2-gtk-layer-shell-0.1
```

Python dependencies:

```bash
cd platform/desktop-shell
python3 -m pip install -r requirements.txt
```

## Run

```bash
cd platform/desktop-shell
python3 main.py
```

or

```bash
cd platform/desktop-shell
./scripts/run.sh
```

## Configuration

On first run, config is created at:

- `~/.config/nemos/shell.yaml`

Supported keys:

- `app_name`
- `logo_text`
- `theme` (`dark` or `light`)
- `dock_autohide_delay_ms`
- `orchestration_url`
- `pinned_apps` list with `name`, `exec`, `icon`

You can also start from:

- `config/shell.yaml`

## Orchestration integration

The AI bar expects Phase 2 API endpoints:

- `POST /tasks`
- `GET /tasks/{task_id}`
- `GET /approvals/pending`
- `POST /approvals/submit`

Default URL is `http://127.0.0.1:11431` and can be changed in config.
