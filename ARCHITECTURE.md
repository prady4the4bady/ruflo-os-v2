# Prady OS Architecture

This document summarizes how Phases 1 through 5 connect in a single executable path.

## Phase Map

1. Phase 1: Model Gateway (`ai-core/model-gateway`)
2. Phase 2: Orchestration Workflow Engine (`orchestration/workflow-engine`)
3. Phase 3: Automation Substrate (`automation/playwright-runner`, `automation/screen-operator`)
4. Phase 4: Desktop Shell (`platform/desktop-shell`)
5. Phase 5: Model Manager (`platform/model-manager`)

## Runtime Data Flow

1. A client submits a task goal to the workflow engine at port `11431`.
2. Conductor decomposes the goal into subtasks and executes them with dependency ordering.
3. Browser subtasks are delegated to Playwright runner (Phase 3).
4. File subtasks persist artifacts for the user environment.
5. Model gateway (Phase 1) remains available for planning/summarization and model-backed tasks.
6. Model manager (Phase 5) maintains model registry/routing policy state for gateway-facing configuration.
7. Desktop shell (Phase 4) is the interactive UX layer that can consume orchestration/model services.

## End-to-End HN Task

Implemented and tested at `tests/e2e/test_hn_task.py`:

- Goal: open Hacker News, extract top story title, write to `~/Desktop/top-story.txt`
- Browser execution: Playwright runner
- Write execution: file agent
- Validation: orchestration completion + file existence + non-empty title

## Integration Stack

Root compose file: `docker-compose.dev.yml`

Services:

- `redis`
- `model-gateway` (`11430`)
- `workflow-engine` (`11431`)
- `playwright-runner` (internal)
- `model-manager` (`11432`)

This stack is controlled by:

```bash
make dev-up
make test-e2e
make dev-down
```
