# Prady Model Manager (Phase 5)

Model manager provides a Python CLI and a minimal web UI for installing, validating, registering, and routing local GGUF models.

## Features

- `prady-models list`
- `prady-models add --hf-repo ... --file ...`
- `prady-models add --github-url ...`
- `prady-models remove <model-id>`
- `prady-models set-default <model-id> --capability coding|chat|vision`
- `prady-models serve` web UI on `localhost:11432`

Each add pipeline performs:

1. Source validation (HF API repo/file existence or GitHub URL reachability)
2. SHA256 integrity verification (HF LFS hash when available, optional explicit hash override)
3. Download into `~/.nemos/models/`
4. Metadata extraction (architecture, context length, quantization)
5. RAM estimate from model size + quantization
6. Registry write to Phase 1 model registry: `ai-core/model-gateway/config/model-registry.yaml`
7. Warmup inference (`hello`) via Ollama or llama-cpp-python fallback
8. Rollback on any failure (registry removal + downloaded file cleanup + model cleanup)

All actions are logged to:

- `platform/model-manager/logs/model-manager.jsonl`

## Install

```bash
cd platform/model-manager
python3 -m pip install -r requirements-dev.txt
python3 -m pip install -e .
```

## CLI usage

```bash
prady-models list

prady-models add \
  --hf-repo "TheBloke/Mistral-7B-Instruct-v0.2-GGUF" \
  --file "mistral-7b-instruct-v0.2.Q4_K_M.gguf"

prady-models add \
  --github-url "https://github.com/org/repo/releases/download/v1/model.gguf"

prady-models remove local-mistral-7b-instruct-v0.2.q4_k_m

prady-models set-default local-mistral-7b-instruct-v0.2.q4_k_m --capability coding
```

## Web UI

```bash
cd platform/model-manager
python3 -m prady_models.cli serve
```

Open:

- [http://127.0.0.1:11432](http://127.0.0.1:11432)

The UI shows model cards (name, capabilities, RAM estimate, status), install/remove actions, and routing policy editor.

## Tests

```bash
cd platform/model-manager
python3 -m pytest tests -q
```

Covers:

- download + validation behavior
- registry writes
- rollback behavior on warmup failure
