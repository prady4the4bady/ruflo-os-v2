from __future__ import annotations

from gi.repository import Gdk, Gtk

from prady_shell.config import ShellConfig
from prady_shell.services.orchestration import OrchestrationClient
from prady_shell.services.search import SearchService
from prady_shell.widgets.ai_task_bar import AITaskBar
from prady_shell.widgets.dock import Dock
from prady_shell.widgets.launcher import SpotlightLauncher
from prady_shell.widgets.notifications import NotificationsCenter
from prady_shell.widgets.top_bar import TopBar


class ShellWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, config: ShellConfig):
        super().__init__(application=app)
        self._config = config
        self.set_title("Prady Desktop Shell")
        self.set_default_size(1600, 900)
        self.set_decorated(False)

        self._layer_shell_enabled = self._try_enable_layer_shell()
        if not self._layer_shell_enabled:
            self.maximize()

        overlay = Gtk.Overlay()
        self.set_child(overlay)

        base = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        overlay.set_child(base)

        self.notifications = NotificationsCenter()

        self.top_bar = TopBar(
            logo_text=config.logo_text,
            app_name=config.app_name,
            on_toggle_notifications=self.notifications.toggle,
        )

        orchestration = OrchestrationClient(config.orchestration_url)
        self.ai_bar = AITaskBar(orchestration, self._add_notification, self.top_bar.set_ai_state)

        self.dock = Dock(
            pinned_apps=config.pinned_apps,
            autohide_delay_ms=config.dock_autohide_delay_ms,
            on_notify=self._add_notification,
        )

        self.launcher = SpotlightLauncher(SearchService(), self._add_notification, self.ai_bar.submit_goal)

        top_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        top_wrap.append(self.top_bar)
        top_wrap.set_valign(Gtk.Align.START)
        top_wrap.set_halign(Gtk.Align.FILL)

        ai_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        ai_wrap.append(self.ai_bar)
        ai_wrap.set_valign(Gtk.Align.END)
        ai_wrap.set_halign(Gtk.Align.FILL)

        dock_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        dock_wrap.append(self.dock)
        dock_wrap.set_valign(Gtk.Align.END)
        dock_wrap.set_halign(Gtk.Align.CENTER)

        notif_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        notif_wrap.append(self.notifications)
        notif_wrap.set_valign(Gtk.Align.START)
        notif_wrap.set_halign(Gtk.Align.END)

        launcher_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        launcher_wrap.append(self.launcher)
        launcher_wrap.set_halign(Gtk.Align.CENTER)
        launcher_wrap.set_valign(Gtk.Align.CENTER)

        overlay.add_overlay(top_wrap)
        overlay.add_overlay(ai_wrap)
        overlay.add_overlay(dock_wrap)
        overlay.add_overlay(notif_wrap)
        overlay.add_overlay(launcher_wrap)

        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        self._add_notification("Shell", "Desktop shell ready", "success")

    def _try_enable_layer_shell(self) -> bool:
        try:
            import gi

            gi.require_version("GtkLayerShell", "0.1")
            from gi.repository import GtkLayerShell

            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            return True
        except Exception:
            return False

    def _on_key_pressed(self, _controller, keyval: int, _keycode: int, _state: int) -> bool:
        if keyval in (Gdk.KEY_Super_L, Gdk.KEY_Super_R):
            self.launcher.toggle()
            return True

        if keyval == Gdk.KEY_Escape:
            self.launcher.hide_launcher()
            return True

        return False

    def _add_notification(self, title: str, message: str, kind: str) -> None:
        self.notifications.add_notification(title, message, kind)
