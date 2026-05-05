from __future__ import annotations

import shlex
import subprocess
from typing import Callable

from gi.repository import GLib, Gtk


class Dock(Gtk.Revealer):
    def __init__(
        self,
        pinned_apps: list[dict[str, str]],
        autohide_delay_ms: int,
        on_notify: Callable[[str, str, str], None],
    ) -> None:
        super().__init__()
        self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.set_transition_duration(240)
        self.set_reveal_child(True)
        self._on_notify = on_notify
        self._pinned_apps = pinned_apps
        self._autohide_delay_ms = autohide_delay_ms
        self._running_names: set[str] = set()

        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        wrap.add_css_class("dock-wrap")
        wrap.set_margin_bottom(14)
        wrap.set_margin_start(18)
        wrap.set_margin_end(18)
        wrap.set_margin_top(6)

        self._row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._row.set_margin_top(8)
        self._row.set_margin_bottom(8)
        self._row.set_margin_start(10)
        self._row.set_margin_end(10)
        wrap.append(self._row)
        self.set_child(wrap)

        motion = Gtk.EventControllerMotion()
        motion.connect("enter", self._on_mouse_enter)
        motion.connect("leave", self._on_mouse_leave)
        wrap.add_controller(motion)

        self.refresh_running_apps()
        GLib.timeout_add_seconds(4, self._scheduled_refresh)

    def _on_mouse_enter(self, *_args) -> None:
        self.set_reveal_child(True)

    def _on_mouse_leave(self, *_args) -> None:
        GLib.timeout_add(self._autohide_delay_ms, self._do_hide)

    def _do_hide(self) -> bool:
        self.set_reveal_child(False)
        return False

    def _scheduled_refresh(self) -> bool:
        self.refresh_running_apps()
        return True

    def refresh_running_apps(self) -> None:
        self._running_names = self._detect_running_app_names()
        while (child := self._row.get_first_child()) is not None:
            self._row.remove(child)

        for app in self._pinned_apps:
            self._row.append(self._build_app_button(app))

    def _detect_running_app_names(self) -> set[str]:
        names: set[str] = set()
        try:
            import psutil

            for proc in psutil.process_iter(["name"]):
                proc_name = (proc.info.get("name") or "").strip().lower()
                if proc_name:
                    names.add(proc_name)
        except Exception:
            return set()
        return names

    def _is_app_running(self, app: dict[str, str]) -> bool:
        app_name = app.get("name", "").lower()
        for proc_name in self._running_names:
            if app_name and app_name in proc_name:
                return True
        return False

    def _build_app_button(self, app: dict[str, str]) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        btn = Gtk.Button(label=app.get("name", "App"))
        btn.add_css_class("dock-item")
        btn.connect("clicked", lambda *_: self._launch(app))

        gesture = Gtk.GestureClick()
        gesture.set_button(3)
        gesture.connect("pressed", lambda g, n, x, y: self._show_context_menu(btn, app))
        btn.add_controller(gesture)

        dot = Gtk.Label(label="•" if self._is_app_running(app) else "")
        dot.add_css_class("dock-dot")
        dot.set_halign(Gtk.Align.CENTER)

        box.append(btn)
        box.append(dot)
        return box

    def _show_context_menu(self, parent: Gtk.Widget, app: dict[str, str]) -> None:
        pop = Gtk.Popover()
        pop.set_parent(parent)

        menu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        menu.set_margin_top(8)
        menu.set_margin_bottom(8)
        menu.set_margin_start(8)
        menu.set_margin_end(8)

        open_btn = Gtk.Button(label=f"Open {app.get('name', 'App')}")
        open_btn.connect("clicked", lambda *_: self._launch(app))
        quit_btn = Gtk.Button(label="Hide Dock")
        quit_btn.connect("clicked", lambda *_: self.set_reveal_child(False))

        menu.append(open_btn)
        menu.append(quit_btn)
        pop.set_child(menu)
        pop.popup()

    def _launch(self, app: dict[str, str]) -> None:
        exec_cmd = app.get("exec", "")
        if not exec_cmd:
            self._on_notify("Dock", "App command is missing", "error")
            return

        try:
            subprocess.Popen(shlex.split(exec_cmd))
            self._on_notify("Dock", f"Launching {app.get('name', 'app')}", "info")
        except Exception as exc:
            self._on_notify("Dock", f"Failed to launch: {exc}", "error")
