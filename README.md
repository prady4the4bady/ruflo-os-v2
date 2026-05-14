# PRADY OS

> Open-source AI-native Linux OS.
> Prax controls your device. You supervise.
> Built by Pradyun — Dubai, UAE — 2026

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Kernel](https://img.shields.io/badge/kernel-prady4the4bady%2Flinux-orange)
![Services](https://img.shields.io/badge/services-44-purple)
![Release](https://img.shields.io/badge/release-v1.0.0-brightgreen)

## What Prady OS is

Prady OS is a Linux operating system where the AI agent (Prax) controls the device autonomously.
The user assigns tasks or simply approves what Prax proposes. Prax handles the rest — research,
building, testing, publishing.

This is not a demo. Every feature listed below has a passing test and runs on real hardware.

## Architecture

```
PRADY OS
  └── KRYOS (orchestration engine)
        └── PRAX (autonomous agent)
              ├── LUMYN (deep reasoning sub-agent)
              └── VYREX (AI inference proxy)
                    ├── Local: Ollama + HuggingFace models
                    └── Cloud: OpenAI-compatible passthrough
```

## What Prax can do — verified by tests

| Feature | How | Test File |
|---------|-----|-----------|
| Controls cursor and keyboard | xdotool/ydotool via computer-use | Phase 8 tests |
| Sees the screen | vision-agent service | Phase 8 tests |
| Hears and speaks offline | Whisper STT + Piper TTS | Phase 31 tests |
| Learns from every task | Skill store + LoRA scheduler | Phase 35 tests |
| Monitors hardware 24/7 | Isolation Forest anomaly detection | Phase 36 tests |
| Triages hardware before boot | UEFI BIOS AI Stage 1 + Stage 2 | Phase 34 tests |
| Updates itself safely | A/B partition + rollback | Phase 30 tests |
| Sandboxes third-party apps | Docker + SDK registry | Phase 37 tests |
| Discovers unsolved problems | ArXiv + HN + GitHub scanner | Phase 39 tests |
| Builds complete projects | 6-agent pipeline with git commits | Phase 39 tests |
| Verifies cold-start before delivery | Docker clean container check | Phase 39 tests |
| Publishes to social media honestly | Twitter/Reddit/HN/PH APIs | Phase 40 tests |
| Analyses market with free data | GitHub + npm APIs | Phase 40 tests |
| Generates investor pitch PDF | reportlab, honest metrics only | Phase 40 tests |
| Organises filesystem | Duplicate finder, approval required | Phase 40 tests |
| Researches when system is idle | CPU + RAM monitor, auto-trigger | Phase 41 |
| Sends weekly honest digest | Monday 9AM via notification-bus | Phase 41 tests |

## What Prax does NOT claim

- Active user counts (always shown as "—" — never fabricated)
- Revenue (zero until real transactions exist)
- Market size (only cited from free data sources)
- "Revolutionary" or "game-changing" (these words are forbidden in the content generator source code)

## Install on real hardware

```bash
# Download the signed ISO
wget https://github.com/prady4the4bady/prady-os/releases/download/v1.0.0/prady-os-v1.0.0-signed.iso

# Verify integrity
sha256sum -c prady-os-v1.0.0-signed.iso.sha256

# Write to USB (replace /dev/sdX with your drive)
bash build/iso/scripts/write_usb.sh /dev/sdX

# Boot and complete the setup wizard
# Say "Hey Prady" — Prax takes it from there
```

## Quick start for developers

```bash
git clone https://github.com/prady4the4bady/prady-os
cd prady-os
docker compose -f docker-compose.dev.yml up -d
cd ui/desktop-shell && npm install && npm run dev
# Visit http://localhost:5173
```

## Run the test suite

```bash
python -m pytest platform/ -W error::DeprecationWarning -q
```

## Service map (44 services)

| Port | Service | Purpose |
|------|---------|---------|
| 3000 | desktop-shell | macOS-style React UI |
| 8000+ | model-gateway | Central AI routing |
| 8002 | model-manager | Model lifecycle |
| 8004 | kryos-swarm | Multi-agent orchestration |
| 8011 | loop-runner | Background task loop |
| 8012 | ota-service | A/B partition updates |
| 8013 | auth-service | JWT + PAM authentication |
| 8014 | voice-service | Whisper STT + Piper TTS |
| 8017 | bios-ai | UEFI pre-boot intelligence |
| 8018 | self-learning | Skill store + LoRA trainer |
| 8019 | hardware-intel | Sensor anomaly detection |
| 8020 | sdk-registry | Third-party app sandbox |
| 8021 | system-health | Unified health aggregator |
| 8022 | inventor-engine | Autonomous project inventor |
| 8023 | social-publisher | Honest social media posts |
| 8024 | market-intel | Free market data analysis |
| 8025 | biz-docs | Investor pitch + metrics |
| 8026 | system-organizer | Filesystem organisation |
| 8090 | bot-bridge | Telegram/Discord bridge |
| 8091 | vision-agent | Screen capture + analysis |
| 8092 | input-controller | Keyboard/mouse control |
| 8093 | process-manager | Process lifecycle |
| 8094 | memory-store | ChromaDB vector store |
| 8099 | oobe-service | First-boot setup wizard |
| 8100 | agent-runtime | Prax agent runtime |
| 8101 | automation-service | Desktop automation |
| 8105 | vyrex-proxy | AI inference proxy |
| 8106 | computer-use | Screen/cursor/keyboard |
| 8108 | memory-service | Memory management |
| 8110 | task-scheduler | Job scheduling |
| 8111 | notification-bus | Event notifications |
| 8112 | audit-log | Append-only event log |
| 8113 | model-hub | Model download hub |
| 8114 | persona-service | Persona management |
| 8115 | watchdog | Service health monitor |
| 8116 | package-manager | Package installation |
| 8117 | security-policy | Permission enforcement |
| 8118 | ebpf-hardening | Kernel syscall sandbox |
| 8120 | kryos-researcher | Problem discovery agent |
| 8121 | proposal-gate | User approval gateway |
| 11430 | model-gateway | AI routing (alt port) |
| 11431 | workflow-engine | Workflow execution |
| 11433 | vyrex (GPU) | GPU inference server |

## License

MIT — free to use, modify, and distribute forever.

## Honesty statement

This project was built autonomously by Prax, an AI agent running on Prady OS.
All code was written by AI agents and reviewed by Pradyun.
Every feature has a passing test. If something does not work, it is documented
in [HONEST_LIMITATIONS.md](HONEST_LIMITATIONS.md), not hidden.
