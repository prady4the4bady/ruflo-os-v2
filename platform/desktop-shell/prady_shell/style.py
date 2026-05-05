from __future__ import annotations

from gi.repository import Gdk, Gtk


def css_for_theme(theme: str) -> str:
    is_light = theme == "light"

    bg = "rgba(242,242,246,0.88)" if is_light else "rgba(14,16,20,0.78)"
    panel = "rgba(255,255,255,0.82)" if is_light else "rgba(26,28,36,0.72)"
    text = "#0d1321" if is_light else "#eef3ff"
    subtext = "#4b5563" if is_light else "#a9b5d0"

    return f"""
    * {{
      color: {text};
      font-family: "SF Pro Display", "Inter", sans-serif;
    }}

    window {{
      background: transparent;
    }}

    .frosted {{
      background: {bg};
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.16);
      box-shadow: 0 10px 30px rgba(0,0,0,0.24);
      padding: 8px 12px;
    }}

    .shell-topbar, .ai-taskbar, .dock-wrap, .notif-panel, .launcher-box {{
      background: {panel};
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.20);
    }}

    .muted {{
      color: {subtext};
    }}

    .status-dot {{
      border-radius: 9999px;
      min-width: 10px;
      min-height: 10px;
      margin-right: 6px;
    }}

    .status-idle {{ background: #9ca3af; }}
    .status-thinking {{ background: #f59e0b; }}
    .status-executing {{ background: #10b981; }}

    .dock-item {{
      border-radius: 12px;
      padding: 6px;
    }}

    .dock-dot {{
      color: #60a5fa;
      font-weight: 700;
      font-size: 14px;
    }}

    .launcher-row:selected {{
      background: rgba(96,165,250,0.22);
      border-radius: 10px;
    }}
    """


def apply_css(theme: str) -> None:
    provider = Gtk.CssProvider()
    provider.load_from_data(css_for_theme(theme).encode("utf-8"))
    display = Gdk.Display.get_default()
    if display is not None:
        Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
