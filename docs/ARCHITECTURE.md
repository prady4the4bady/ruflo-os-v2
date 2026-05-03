┌─────────────────────────────────────────────────────┐
│                   USER INTERFACE                     │
│  PradyBar (AGS) │ PradyDock (AGS) │ Spotlight (AGS) │
│  PradyAssistant (AGS) │ System Preferences           │
├─────────────────────────────────────────────────────┤
│              WAYLAND COMPOSITOR                      │
│         Hyprland + prady-hyprland-config             │
│    blur │ rounded corners │ spring animations         │
├─────────────────────────────────────────────────────┤
│              PRADY AGENT (TypeScript)                │
│  ReAct Loop │ Lumyn Planner │ Tool Registry          │
│  mouse/keyboard/screen tools via ydotool/grim        │
├─────────────────────────────────────────────────────┤
│              VYREX (Go + llama.cpp)               │
│  Model Registry │ OpenAI API Socket │ Hot-swap        │
│  Qwen2.5-7B │ LLaVA │ Whisper │ Cloud fallback        │
├─────────────────────────────────────────────────────┤
│              LINUX KERNEL (Debian bookworm)          │
│  eBPF sandbox │ uinput │ io_uring IPC │ PipeWire      │
└─────────────────────────────────────────────────────┘
