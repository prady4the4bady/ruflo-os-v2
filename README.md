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

Prady OS is a Linux operating system where Prax — the AI agent — controls the device autonomously
on your behalf. You assign a task or approve what Prax proposes. Prax handles the rest: research,
building, testing, verifying, and publishing.

This is not a demo. Every feature listed below has a passing test. Known limitations are documented
in [HONEST_LIMITATIONS.md](HONEST_LIMITATIONS.md).

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

| Feature | Verified by |
|---------|------------|
| Controls cursor and keyboard | computer-use tests |
| Sees the screen | vision-agent tests |
| Hears and speaks offline (Whisper + Piper) | voice-service tests |
| Learns from every task (skill store) | self-learning tests |
| Monitors hardware 24/7 (Isolation Forest) | hardware-intel tests |
| Triages hardware before boot (BIOS AI) | bios-ai tests |
| Updates itself safely (A/B partition) | ota-service tests |
| Sandboxes third-party apps (SDK registry) | sdk-registry tests |
| Discovers unsolved problems (ArXiv + HN + GitHub) | inventor-engine tests |
| Builds complete verified projects (6-agent pipeline) | inventor-engine tests |
| Verifies cold-start before every delivery | verifier-agent tests |
| Publishes to social media honestly | social-publisher tests |
| Analyses market with free data only | market-intel tests |
| Generates investor pitch PDFs | biz-docs tests |
| Organises filesystem with user approval | system-organizer tests |
| Researches when system is idle | Phase 41 tests |
| Sends honest weekly digest every Monday | Phase 41 tests |

## What Prax does NOT claim

- **Active users**: always shown as null — never fabricated
- **Revenue**: zero until real transactions exist
- **Market size**: only cited from free verifiable sources
- **"Revolutionary"**: this word is forbidden in the content generator source code (verified by test)

See [HONEST_LIMITATIONS.md](HONEST_LIMITATIONS.md) for what requires specific hardware, what is a
stub, and what requires external credentials to function.

## Install on real hardware

```bash
# Download
wget https://github.com/prady4the4bady/prady-os/releases/download/v1.0.0/prady-os-v1.0.0-signed.iso

# Verify
sha256sum -c prady-os-v1.0.0-signed.iso.sha256

# Write to USB (replace /dev/sdX)
bash build/iso/scripts/write_usb.sh /dev/sdX

# Boot and complete the 7-step setup wizard
# Say "Hey Prady" — Prax takes it from there
```

## Developer quick start

```bash
git clone https://github.com/prady4the4bady/prady-os
cd prady-os
docker compose -f docker-compose.dev.yml up -d
cd ui/desktop-shell && npm install && npm run dev
# Visit http://localhost:5173
```

## Run the tests

```bash
python -m pytest platform/ -W error::DeprecationWarning -q
```

## Service map (44 services)

| Port | Service | Purpose |
|------|---------|---------|
| 3000 | desktop-shell | macOS-style React UI |
| 8002 | computer-use | Screen/cursor/keyboard control |
| 8012 | ota-service | A/B partition updates |
| 8013 | auth-service | JWT + PAM authentication |
| 8014 | voice-service | Whisper STT + Piper TTS |
| 8017 | bios-ai | UEFI pre-boot intelligence |
| 8018 | self-learning | Skill store + LoRA scheduler |
| 8019 | hardware-intel | Sensor anomaly detection |
| 8020 | sdk-registry | Third-party app sandbox |
| 8021 | system-health | Unified health aggregator |
| 8022 | inventor-engine | Autonomous project inventor |
| 8023 | social-publisher | Honest social media posts |
| 8024 | market-intel | Free market data analysis |
| 8025 | biz-docs | Investor pitch + metrics |
| 8026 | system-organizer | Filesystem organisation |
| 8099 | oobe-service | First-boot setup wizard |
| 8105 | vyrex-proxy | AI inference proxy |
| 8111 | notification-bus | Event notifications |
| 8112 | audit-log | Append-only event log |
| 8117 | security-policy | Permission enforcement |
| 8118 | ebpf-hardening | Kernel syscall sandbox |
| 8120 | kryos-researcher | Problem discovery agent |
| 8121 | proposal-gate | User approval gateway |
| +21 more | +21 more services | See docker-compose.dev.yml |

## License

MIT — free to use, modify, and distribute forever.

## Honesty statement

Every feature listed above has a passing test. Every limitation is documented in
[HONEST_LIMITATIONS.md](HONEST_LIMITATIONS.md). Prax was built by AI agents and reviewed by Pradyun.
If something does not work, it is documented — not hidden.
