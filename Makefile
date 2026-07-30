.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help setup dev stop migrate seed test lint format typecheck e2e reset-db api-shell logs

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n",$$1,$$2}'

setup: ## Install all dependencies (JS + Python) and copy env
	@[ -f .env ] || cp .env.example .env
	corepack enable && pnpm install
	cd apps/api && python -m venv .venv && . .venv/Scripts/activate 2>/dev/null || . .venv/bin/activate; pip install -e ".[dev]"

dev: ## Start the full stack via Docker Compose
	$(COMPOSE) up --build

stop: ## Stop the stack
	$(COMPOSE) down

migrate: ## Run Alembic migrations against the running DB
	$(COMPOSE) exec api alembic upgrade head

seed: ## Load the UK demo seed data
	$(COMPOSE) exec api python -m app.seed --reset

test: ## Run all tests (Python + JS)
	cd apps/api && pytest -q
	pnpm --filter web test

lint: ## Lint everything
	cd apps/api && ruff check . && cd -
	pnpm --filter web lint

format: ## Auto-format everything
	cd apps/api && ruff format . && cd -
	pnpm format

typecheck: ## Type-check Python (mypy) and TS (tsc)
	cd apps/api && mypy app && cd -
	pnpm --filter web typecheck

e2e: ## Run Playwright end-to-end tests
	pnpm --filter web exec playwright test

reset-db: ## Drop and recreate the database volume, migrate + seed
	$(COMPOSE) down -v
	$(COMPOSE) up -d db
	$(COMPOSE) run --rm api sh -c "alembic upgrade head && python -m app.seed --reset"

logs: ## Tail service logs
	$(COMPOSE) logs -f
