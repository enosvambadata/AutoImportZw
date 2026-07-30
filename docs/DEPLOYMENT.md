# Deployment

## Local (Docker Compose)

```bash
cp .env.example .env
docker compose up --build
```

Compose starts three services with health checks:

- **db** — PostgreSQL 16 (named volume `db_data`), `pg_isready` health check.
- **api** — runs `alembic upgrade head`, seeds demo data if empty, serves Uvicorn on `:8000`. Health
  check hits `/health`.
- **web** — Next.js standalone server on `:3000`, starts only after the API is healthy.

## Configuration

All configuration is environment-driven (see `.env.example`). Critical for production:

| Variable | Production value |
|----------|------------------|
| `JWT_SECRET_KEY` | strong random secret from a secrets manager |
| `API_ENV` | `production` (enables HSTS) |
| `COOKIE_SECURE` | `true` (HTTPS only) |
| `CORS_ORIGINS` | your web origin(s) |
| `DATABASE_URL` / `DATABASE_URL_SYNC` | managed Postgres (async `asyncpg`, sync `psycopg`) |
| `NEXT_PUBLIC_API_BASE_URL` | public API base URL |

## Migrations & seed

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed --if-empty   # or --reset
```

Migrations are the schema authority in production. (For dev/first-run convenience the API also
`create_all`s tables when using SQLite.)

## Running without Docker

- **API**: `pip install -e ".[dev]"`, `alembic upgrade head`, `uvicorn app.main:app` behind a process
  manager. Scale with multiple Uvicorn/Gunicorn workers behind a reverse proxy (TLS termination).
- **Web**: `npm run build && npm start` (standalone output) or deploy to a Node host / platform.

## Operational notes

- Replace the in-process rate limiter and audit writer with Redis / a durable queue for multi-instance
  deployments.
- Back up the Postgres volume; run migrations as a pre-deploy step.
- Add centralised logging/metrics; the request ID (`X-Request-ID`) is echoed on every response for
  correlation.

## Scheduled daily shortlist

Run the prospect job every morning; it scans each dealership's cars **due that day** and delivers a
ranked shortlist. It reads listings already in the database (no scraping).

```bash
# cron (07:00 daily), inside the api container/host:
0 7 * * *  cd /app && python -m app.jobs.daily_shortlist
# or via compose:
docker compose exec api python -m app.jobs.daily_shortlist
```

On Windows use Task Scheduler (daily 07:00 running the same command); or add a scheduled GitHub Actions
workflow. Set `PROSPECTS_DIR` for the JSON output location, or implement `deliver()` in
`app/jobs/daily_shortlist.py` to email/Slack/webhook the prospects. To pull a real catalogue from a
named auctioneer, configure the official-API connector (`AUCTIONEER_API_URL`, `AUCTIONEER_API_KEY`) —
see [API_INTEGRATIONS.md](API_INTEGRATIONS.md); credential scraping of the auction website is not
supported.

## CI

`.github/workflows/ci.yml` runs backend lint (ruff), type-check (mypy, advisory), Alembic migrations
against a Postgres service container, pytest, and the frontend lint/typecheck/tests/build.
