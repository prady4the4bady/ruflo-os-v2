from __future__ import annotations

import shlex
import subprocess
from typing import Callable

from gi.repository import Gtk

from prady_shell.services.search import SearchItem, SearchService


class SpotlightLauncher(Gtk.Revealer):
    def __init__(
        self,
        search_service: SearchService,
        on_notify: Callable[[str, str, str], None],
        on_ai_goal: Callable[[str], None],
    ) -> None:
        super().__init__()
        self.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        self.set_transition_duration(150)
        self.set_reveal_child(False)

        self._search = search_service
        self._on_notify = on_notify
        self._on_ai_goal = on_ai_goal
        self._results: list[SearchItem] = []

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.add_css_class("launcher-box")
        outer.set_size_request(720, 420)
        outer.set_margin_top(90)
        outer.set_margin_bottom(90)

        self._entry = Gtk.Entry()
        self._entry.set_placeholder_text("Search apps, files, settings, or ask AI")
        self._entry.set_margin_top(12)
        self._entry.set_margin_start(12)
        self._entry.set_margin_end(12)
        self._entry.connect("changed", self._on_entry_changed)
        self._entry.connect("activate", self._on_activate)

        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._list.connect("row-activated", self._on_row_activated)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_margin_start(10)
        scroll.set_margin_end(10)
        scroll.set_margin_bottom(10)
        scroll.set_child(self._list)

        outer.append(self._entry)
        outer.append(scroll)
        self.set_child(outer)

    def toggle(self) -> None:
        is_visible = self.get_reveal_child()
        self.set_reveal_child(not is_visible)
        if not is_visible:
            self._entry.set_text("")
            self._entry.grab_focus()

    def hide_launcher(self) -> None:
        self.set_reveal_child(False)

    def _on_entry_changed(self, *_args) -> None:
        query = self._entry.get_text()
        self._results = self._search.search(query)
        self._render_results()

    def _render_results(self) -> None:
        while (child := self._list.get_first_child()) is not None:
            self._list.remove(child)

        for item in self._results:
            row = Gtk.ListBoxRow()
            row.add_css_class("launcher-row")

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.set_margin_top(8)
            box.set_margin_bottom(8)
            box.set_margin_start(8)
            box.set_margin_end(8)

            title = Gtk.Label(label=item.title)
            title.set_xalign(0)
            subtitle = Gtk.Label(label=item.subtitle)
            subtitle.set_xalign(0)
            subtitle.add_css_class("muted")

            box.append(title)
            box.append(subtitle)
            row.set_child(box)
            self._list.append(row)

        first = self._list.get_row_at_index(0)
        if first:
            self._list.select_row(first)

    def _on_activate(self, *_args) -> None:
        row = self._list.get_selected_row()
        if row is None:
            return
        self._execute_row(row)

    def _on_row_activated(self, _list, row: Gtk.ListBoxRow) -> None:
        self._execute_row(row)

    def _execute_row(self, row: Gtk.ListBoxRow) -> None:
        idx = row.get_index()
        if idx < 0 or idx >= len(self._results):
            return

        item = self._results[idx]
        if item.kind in {"app", "setting"}:
            try:
                subprocess.Popen(shlex.split(item.payload.get("exec", "")))
            except Exception as exc:
                self._on_notify("Launcher", f"Failed to launch: {exc}", "error")
                return
            self._on_notify("Launcher", f"Launched {item.title}", "info")
        elif item.kind == "file":
            try:
                subprocess.Popen(["xdg-open", item.payload.get("path", "")])
            except Exception as exc:
                self._on_notify("Launcher", f"Failed to open file: {exc}", "error")
                return
            self._on_notify("Launcher", f"Opened {item.title}", "info")
        elif item.kind == "ai":
            self._on_ai_goal(item.payload.get("goal", ""))

        self.hide_launcher()
