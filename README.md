# AutoBid Intelligence

A decision-support platform for independent UK motor dealers buying at auction. It estimates the
**safe** and **absolute** maximum hammer bids, break-even bid, expected/worst/best-case profit, ROI
and a transparent **BUY / CONSIDER / PASS** recommendation with plain-English reasons.

> **Decision support only — not a guarantee of profit.** Recommendations are estimates that depend on
> the accuracy of entered and third-party data. A physical and mechanical inspection may still be
> required; hidden defects can materially affect profit. Users remain responsible for all bidding and
> purchasing decisions.

## Product overview

- **Calculation engine** (Python, `Decimal`) is the single source of truth for every monetary figure:
  fee strategies (fixed / percentage / tiered / percentage+fixed, min/max, VAT), bid solving via
  bisection (fees that depend on hammer price are handled correctly), profit scenarios, ROI, a bid
  ladder and a sensitivity matrix.
- **Risk engine** — configurable weighted score (0–100) across 12 factors, with critical hard flags.
- **Recommendation engine** — a documented rules engine (not ML) returning decision, reasons,
  positive/warning factors, missing information, next action and a confidence level.
- **Full stack** — FastAPI + SQLAlchemy 2 + PostgreSQL, Next.js (App Router) + Tailwind, JWT auth with
  refresh-token rotation, RBAC, an append-only audit log, CSV catalogue import and mock data providers
  behind swappable interfaces.

## Screenshots

_Placeholders — capture from a running instance:_

| Screen | File |
|--------|------|
| Dashboard | `docs/screenshots/dashboard.png` |
| Auction listings | `docs/screenshots/listings.png` |
| Appraisal wizard — result | `docs/screenshots/wizard-result.png` |
| Appraisal detail (bid ladder, sensitivity) | `docs/screenshots/appraisal-detail.png` |
| Auction Mode (STOP indicator) | `docs/screenshots/auction-mode.png` |
| Stock & sales | `docs/screenshots/stock.png` |

## Architecture summary

```
apps/web  (Next.js, TypeScript, Tailwind)  ──HTTP──▶  apps/api  (FastAPI, SQLAlchemy 2)  ──▶  PostgreSQL
                                                          │
                                                          ├─ calculations/  (pure Decimal engine — source of truth)
                                                          ├─ services/      (risk, recommendation, evaluation, analytics)
                                                          └─ integrations/  (provider interfaces + mock adapters)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/DATA_MODEL.md](docs/DATA_MODEL.md),
[docs/CALCULATION_ENGINE.md](docs/CALCULATION_ENGINE.md) and
[docs/RECOMMENDATION_RULES.md](docs/RECOMMENDATION_RULES.md).

## Prerequisites

- Docker + Docker Compose **(recommended path)**, or
- Python 3.11+ and Node 20+ for running the apps directly.

## Environment setup

```bash
cp .env.example .env      # adjust secrets for anything beyond local dev
```

Key variables are documented in `.env.example` (database URLs, `JWT_SECRET_KEY`, token TTLs, CORS,
cookie flags, `VAT_RATE`).

## Docker setup (full stack)

```bash
docker compose up --build
```

This starts **PostgreSQL**, the **API** (runs Alembic migrations, seeds demo data if empty, then
serves on `:8000`) and the **web** app on `:3000`. Health checks gate service start-up.

- Web app: http://localhost:3000
- API docs (OpenAPI/Swagger): http://localhost:8000/docs
- API health: http://localhost:8000/health

## Database migrations

```bash
make migrate        # docker compose exec api alembic upgrade head
# or directly:
cd apps/api && alembic upgrade head
```

## Seed commands

```bash
make seed                                   # docker: python -m app.seed --reset
cd apps/api && python -m app.seed --reset   # local
cd apps/api && python -m app.seed --if-empty
```

## Development commands (run apps directly)

```bash
# API
cd apps/api
python -m venv .venv && . .venv/Scripts/activate   # (or .venv/bin/activate)
pip install -e ".[dev]"
alembic upgrade head && python -m app.seed --reset
uvicorn app.main:app --reload

# Web
cd apps/web
npm install
npm run dev        # http://localhost:3000
```

The Makefile wraps the common flows: `make setup | dev | stop | migrate | seed | test | lint |
format | typecheck | e2e | reset-db`.

## Windows desktop launcher

Double-click **`Start AutoBid.bat`** on the Desktop (source in `scripts/start-autobid.bat`). It seeds
the database on first run, starts the API (`:8000`) and web app (`:3000`) in their own windows, waits
until ready, and opens the browser. **`Stop AutoBid.bat`** stops both servers. Requires the one-time
setup (Python venv in `apps/api/.venv` and `npm install` in `apps/web`) to have been done.

## Test commands

```bash
# Backend (calc, risk, recommendation, API integration)
cd apps/api && pytest -q

# Frontend unit tests
cd apps/web && npm run test

# Typecheck / lint
cd apps/api && ruff check app && mypy app
cd apps/web && npm run typecheck && npm run lint

# End-to-end (requires the stack running)
cd apps/web && npx playwright test
```

## Demo users

Password for all: **`Password123!`**

| Role | Email | Can |
|------|-------|-----|
| Administrator | `admin@example.com` | Everything, incl. settings, users, fee schedules |
| Buyer / Appraiser | `buyer@example.com` | Create/edit appraisals, mark purchased/passed, record prep & sales |
| Viewer | `viewer@example.com` | Read-only dashboards and appraisals |

`example.com` is the RFC 2606 documentation domain — clearly not a real address.

## Production considerations

- Replace `JWT_SECRET_KEY` and database credentials with managed secrets.
- Set `COOKIE_SECURE=true`, serve over HTTPS, and set `API_ENV=production` (enables HSTS).
- Swap the in-process rate limiter and audit writer for Redis / a durable queue.
- Replace mock data adapters with licensed providers (see
  [docs/API_INTEGRATIONS.md](docs/API_INTEGRATIONS.md)).
- Run behind a reverse proxy; scale the API with multiple Uvicorn/Gunicorn workers.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) and [docs/SECURITY.md](docs/SECURITY.md).
