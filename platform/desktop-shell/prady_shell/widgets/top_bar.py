from __future__ import annotations

from datetime import datetime

from gi.repository import GLib, Gtk

from prady_shell.services.window_state import ActiveWindowService, SystemStatusService


class TopBar(Gtk.Box):
    def __init__(
        self,
        logo_text: str,
        app_name: str,
        on_toggle_notifications,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.add_css_class("shell-topbar")
        self.set_margin_top(10)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_bottom(6)
        self.set_hexpand(True)

        self._window_service = ActiveWindowService()
        self._system = SystemStatusService()

        self._left = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        logo = Gtk.Label(label=logo_text)
        logo.add_css_class("title-2")
        self._focused = Gtk.Label(label=app_name)
        self._focused.set_xalign(0.0)
        self._left.append(logo)
        self._left.append(self._focused)

        self._center = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._clock = Gtk.Label(label="--:--")
        self._clock.add_css_class("title-3")
        self._center.set_halign(Gtk.Align.CENTER)
        self._center.set_hexpand(True)
        self._center.append(self._clock)

        self._right = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._right.set_halign(Gtk.Align.END)

        self._ai_dot = Gtk.Box()
        self._ai_dot.add_css_class("status-dot")
        self._ai_dot.add_css_class("status-idle")

        self._ai_text = Gtk.Label(label="AI idle")
        self._ai_text.add_css_class("muted")

        self._battery = Gtk.Label(label="--%")
        self._battery.add_css_class("muted")

        self._wifi = Gtk.Label(label="Offline")
        self._wifi.add_css_class("muted")

        self._menu_btn = Gtk.MenuButton(icon_name="avatar-default-symbolic")
        self._menu_btn.set_valign(Gtk.Align.CENTER)

        popover = Gtk.Popover()
        menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        menu_box.set_margin_top(8)
        menu_box.set_margin_bottom(8)
        menu_box.set_margin_start(8)
        menu_box.set_margin_end(8)

        notif_btn = Gtk.Button(label="Notifications")
        notif_btn.connect("clicked", lambda *_: on_toggle_notifications())
        menu_box.append(notif_btn)
        menu_box.append(Gtk.Button(label="Settings"))
        menu_box.append(Gtk.Button(label="Lock"))
        popover.set_child(menu_box)
        self._menu_btn.set_popover(popover)

        self._right.append(self._ai_dot)
        self._right.append(self._ai_text)
        self._right.append(self._battery)
        self._right.append(self._wifi)
        self._right.append(self._menu_btn)

        self.append(self._left)
        self.append(self._center)
        self.append(self._right)

        self._refresh_clock()
        self._refresh_dynamic_labels()
        GLib.timeout_add_seconds(1, self._refresh_clock)
        GLib.timeout_add_seconds(3, self._refresh_dynamic_labels)

    def _refresh_clock(self) -> bool:
        self._clock.set_text(datetime.now().strftime("%a %H:%M"))
        return True

    def _refresh_dynamic_labels(self) -> bool:
        self._focused.set_text(self._window_service.focused_app_name())
        self._battery.set_text(self._system.battery())
        self._wifi.set_text(self._system.wifi())
        return True

    def set_ai_state(self, state: str) -> None:
        self._ai_dot.remove_css_class("status-idle")
        self._ai_dot.remove_css_class("status-thinking")
        self._ai_dot.remove_css_class("status-executing")

        if state == "thinking":
            self._ai_dot.add_css_class("status-thinking")
            self._ai_text.set_text("AI thinking")
        elif state == "executing":
            self._ai_dot.add_css_class("status-executing")
            self._ai_text.set_text("AI executing")
        else:
            self._ai_dot.add_css_class("status-idle")
            self._ai_text.set_text("AI idle")
