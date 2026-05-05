from __future__ import annotations

from gi.repository import Gtk


class NotificationsCenter(Gtk.Revealer):
    def __init__(self) -> None:
        super().__init__()
        self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_LEFT)
        self.set_transition_duration(260)
        self.set_reveal_child(False)

        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        panel.add_css_class("notif-panel")
        panel.set_size_request(360, 460)
        panel.set_margin_top(56)
        panel.set_margin_end(14)
        panel.set_margin_bottom(14)
        panel.set_margin_start(14)

        header = Gtk.Label(label="Notifications")
        header.add_css_class("title-3")
        header.set_margin_top(12)
        header.set_margin_start(12)
        header.set_xalign(0)
        panel.append(header)

        self._stack_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._stack_box.set_margin_start(10)
        self._stack_box.set_margin_end(10)
        self._stack_box.set_margin_bottom(10)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(self._stack_box)

        panel.append(scroll)
        self.set_child(panel)

    def toggle(self) -> None:
        self.set_reveal_child(not self.get_reveal_child())

    def add_notification(self, title: str, body: str, kind: str = "info") -> None:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.add_css_class("frosted")

        title_lbl = Gtk.Label(label=title)
        title_lbl.set_xalign(0)
        title_lbl.add_css_class("title-4")

        body_lbl = Gtk.Label(label=body)
        body_lbl.set_xalign(0)
        body_lbl.add_css_class("muted")
        body_lbl.set_wrap(True)

        badge = Gtk.Label(label=kind.upper())
        badge.set_xalign(0)
        badge.add_css_class("caption")

        card.append(title_lbl)
        card.append(body_lbl)
        card.append(badge)

        self._stack_box.prepend(card)
