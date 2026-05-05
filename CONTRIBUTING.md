# Contributing

This repository is organized in phases. The fastest way to validate cross-phase behavior is the root development stack and E2E test.

## Prerequisites

- Docker + Docker Compose v2
- Python 3.10+
- GNU Make

## Local End-to-End Flow

Use these exact commands:

```bash
make dev-up
make test-e2e
```

What these do:

- `make dev-up`: builds and starts the integration stack from `docker-compose.dev.yml`
- `make test-e2e`: runs `tests/e2e/test_hn_task.py`

To stop the stack:

```bash
make dev-down
```

## E2E Scenario

The end-to-end test validates this path:

1. Submit a goal to the workflow engine.
2. Conductor decomposes into browser + file subtasks.
3. Browser agent extracts Hacker News top story title via Playwright runner.
4. File agent writes output to `~/Desktop/top-story.txt`.
5. Test asserts completion, output file existence, and non-empty content.

## CI

GitHub Actions workflow: `.github/workflows/e2e.yml`.

- Boots stack with `make dev-up`
- Runs headless test via `xvfb-run -a make test-e2e`
- Prints compose logs on failure
