# Honest Limitations — Prady OS v1.0.0

This document lists known limitations, stubs, and features that require specific hardware or setup.
Nothing here is hidden from users. This is the honesty contract.

## Features that require specific hardware

### BIOS AI (Phase 34)
- The UEFI Stage 1 application (PradyBiosAI.c) is compiled and included in the firmware/ directory
  but has NOT been tested on real UEFI hardware in CI
- Requires: x86_64 machine with UEFI firmware
- Fallback: if UEFI AI fails, standard GRUB boots normally
- Status: Stage 2 (post-boot repair) tested on Linux

### Computer-use (screen control)
- Works on X11 with xdotool
- Works on Wayland with ydotool (requires uinput access)
- Does NOT work in Docker containers without a real display (X11 or Wayland socket)
- In containers: returns {success:false, error:"no display available"} — never crashes

### Voice interface (Whisper + Piper)
- Requires a microphone for STT
- Requires speakers for TTS
- In containers without audio devices: Piper returns silence WAV bytes,
  Whisper returns empty transcript
- Both fail gracefully — no crashes

## Features that are functional stubs

### LoRA fine-tuning (Phase 35)
- The lora_trainer.py schedules fine-tuning during idle periods and calls
  vyrex-proxy /v1/fine-tune
- If vyrex-proxy does not expose /v1/fine-tune (most local models do not):
  logs a warning and skips
- Actual LoRA weight updates require: GPU, unsloth or TRL library,
  compatible base model
- Status: scheduler works, actual training requires GPU and model that
  supports fine-tuning

### GGML UEFI inference (Phase 34)
- ModelRunner.c in firmware/uefi-ai/ is a decision stub based on RAM
  and disk health checks
- Full GGML inference inside UEFI requires a custom llama.cpp UEFI port
  which is not yet complete
- Current behavior: rule-based triage only

## Features that require API credentials

### Social publishing (Phase 40)
- Twitter/X: requires TWITTER_API_KEY, TWITTER_API_SECRET,
  TWITTER_BEARER_TOKEN, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
- Reddit: requires REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET,
  REDDIT_USERNAME, REDDIT_PASSWORD
- ProductHunt: requires PRODUCTHUNT_API_KEY
- HackerNews: requires HN_USERNAME, HN_PASSWORD
- Without credentials: platforms are skipped gracefully
- Prady OS itself does not provide these credentials

### GitHub auto-release (Phase 39)
- Requires GITHUB_TOKEN with repo write scope
- Without token: project is saved locally only
- Token is never stored in the codebase

### Model providers (model-gateway)
- OpenAI: requires OPENAI_API_KEY (optional, for cloud fallback)
- Anthropic: requires ANTHROPIC_API_KEY (optional, for cloud fallback)
- NVIDIA NIM: requires NVIDIA_NIM_API_KEY (optional)
- Gemini: requires GEMINI_API_KEY (optional)
- Without any API keys: only local Ollama models work

## Performance notes

### Inventor engine build times
- Simple CLI tools: 2-4 hours
- Web applications: 8-16 hours
- Complex systems: 24-48 hours
- All estimates are honest — Prax does not guarantee project completion
  within any specific time

### Market intelligence accuracy
- GitHub star counts: accurate (live API)
- npm download counts: accurate (live API)
- Market size estimates: NOT provided (we do not estimate without citing a source)
- Competitor analysis: limited to public GitHub and npm data only
- Opportunity score is a heuristic based on competition count — not validated
  against actual market outcomes

## Known issues

### Conftest collision in pytest
- When running `python -m pytest platform/` from the repo root, some hyphenated
  service directories (kryos-researcher, proposal-gate) may have conftest
  import path collisions
- Workaround: run those service tests individually:
  `python -m pytest platform/kryos-researcher/tests/`
- This is a known pytest limitation with hyphenated directory names
