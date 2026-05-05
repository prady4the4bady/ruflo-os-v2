COMPOSE_FILE := docker-compose.dev.yml

.PHONY: up down logs test-all test-phase1 test-phase2 test-phase3 test-phase4 test-phase5 dev-up dev-down test-e2e

up:
	docker compose up --build

down:
	docker compose down --remove-orphans

dev-up:
	docker compose -f $(COMPOSE_FILE) up -d --build

dev-down:
	docker compose -f $(COMPOSE_FILE) down --remove-orphans

logs:
	docker compose logs --tail=200

test-all: test-phase1 test-phase2 test-phase3 test-phase4 test-phase5

test-phase1:
	cd ai-core/model-gateway && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt && pytest tests

test-phase2:
	cd orchestration/workflow-engine && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt && pytest tests

test-phase3:
	cd automation/screen-agent && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt && pytest tests

test-phase4:
	cd desktop/aqua-shell && npm ci && npm test

test-phase5:
	cd agents/lumyn && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt && pytest tests

test-e2e:
	python -m pip install --upgrade pip
	python -m pip install -r tests/e2e/requirements.txt
	python -m pytest tests/e2e/test_hn_task.py -s -v
