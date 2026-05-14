# Contributing

Prady OS v1.0.0 is a 42-phase project. All 42 phases are complete. This guide explains how to run the tests and validate the system locally.

## Prerequisites

- Docker + Docker Compose v2
- Python 3.10+
- GNU Make

## Quick Start

```bash
# Clone and enter the repo
git clone https://github.com/prady4the4bady/prady-os.git
cd prady-os

# Start the development stack (44 services)
make dev-up

# Run the full test suite
make test-e2e

# Stop
make dev-down
```

## What the tests do

- `make dev-up`: builds and starts all services from `docker-compose.dev.yml`
- `make test-e2e`: runs `tests/e2e/test_hn_task.py` which validates cross-service orchestration
- `python -m pytest platform/tests/ -q`: runs the Honesty Contract tests (verify all 44 feature claims)

## CI Workflows

Three workflows run on every push to `main`:

| Workflow | What it checks |
|----------|----------------|
| `Monorepo CI` | Linting, unit tests, all services compile |
| `E2E` | Full end-to-end integration across 44 services |
| `Build Prady OS ISO` | On `v*` tags only: Buildroot ISO compilation + publish |

## Project Structure

| Directory | Phase | Role |
|-----------|-------|------|
| `agents/lumyn` | 1-10 | Core agent runtime |
| `platform/` | 11-20 | Platform services |
| `ai-core/` | 21-30 | AI inference + model gateway |
| `build/` | 31-42 | ISO build pipeline |

## Honesty Policy

Every public claim about Prady OS is verified by a passing test in `platform/tests/test_feature_claims.py`.
If a test fails, the feature claim must be fixed or removed. See `HONEST_LIMITATIONS.md` for known limitations.
