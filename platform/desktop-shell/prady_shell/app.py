from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from prady_shell.config import load_config
from prady_shell.shell_window import ShellWindow
from prady_shell.style import apply_css


class PradyShellApp(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id="org.nemos.desktop-shell")
        self._window: ShellWindow | None = None

    def do_activate(self) -> None:
        config = load_config()
        apply_css(config.theme)

        if self._window is None:
            self._window = ShellWindow(self, config)
        self._window.present()
