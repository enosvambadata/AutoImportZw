# AutoBid Intelligence — Implementation Plan

A decision-support platform for independent UK motor dealers buying at auction. It
estimates safe/absolute/break-even hammer bids, expected/worst/best-case profit, ROI,
risk and a transparent BUY / CONSIDER / PASS recommendation. It **never** guarantees profit.

## Guiding principles

1. **The API is the single source of truth for money.** All financial formulas live in a
   deterministic Python module using `Decimal`. The frontend never re-derives them.
2. **Transparency over "AI".** The recommendation is a documented rules engine. No ML claims.
3. **Real data, mock providers.** Third-party lookups (DVLA, MOT, CAP, Auto Trader) sit behind
   interfaces with clearly-labelled mock adapters. Nothing implies real provider data.
4. **Server-side authorisation.** RBAC is enforced in the API; hiding UI buttons is not security.
5. **Multi-tenancy by dealership.** Every query is scoped to the caller's `dealership_id`.

## Phases

| Phase | Deliverable | Verification |
|-------|-------------|--------------|
| 0 | Planning + assumptions docs | — |
| 1 | Monorepo scaffold, Docker Compose, env, Makefile, CI | files present |
| 2 | Calculation engine (money, fee strategies, bid solver, scenarios, sensitivity, ladder) | pytest |
| 3 | Risk scoring + recommendation engine | pytest |
| 4 | SQLAlchemy models + Alembic migration | import + migration |
| 5 | Auth (Argon2, JWT access/refresh rotation), RBAC dependencies | pytest |
| 6 | REST API `/api/v1` (all entities), integrations, CSV import | pytest (TestClient) |
| 7 | Seed data (UK demo dataset) | seed script runs |
| 8 | Next.js frontend (auth, dashboard, listings, wizard, appraisal, auction mode, stock, settings) | vitest + build |
| 9 | Docs, README, Playwright e2e | — |

## Backend architecture (`apps/api`)

```
app/
  calculations/   pure, deterministic Decimal engine (fees, bids, scenarios, sensitivity, ladder)
  services/       recommendation, risk, audit, analytics, csv_import  (orchestration over engine + repos)
  core/           config, security (hash/jwt), dependencies, rate limiting, errors
  db/             engine/session, Base
  models/         SQLAlchemy 2 declarative models
  schemas/        Pydantic v2 request/response
  repositories/   data-access with dealership scoping
  integrations/   provider interfaces + mock adapters + placeholder real adapters
  api/v1/         FastAPI routers
```

The calculation engine is **framework-free** — it depends only on the stdlib `decimal` module and
plain dataclasses, so it is trivially unit-testable and reusable.

## Frontend architecture (`apps/web`)

Next.js App Router + TypeScript + Tailwind + shadcn-style primitives. A typed API client calls the
FastAPI backend. Zod mirrors *input* validation only; **all money maths is fetched from the API**
(`POST /appraisals/preview`). Auth uses HTTP-only refresh cookie + in-memory access token.

## Testing strategy

- **Calc unit tests** — fee types, tier boundaries, VAT, zero/negative profit, rounding, iterative fees, scenarios, sensitivity.
- **Recommendation tests** — every outcome + blocking flags.
- **API integration tests** — auth, RBAC, dealership isolation, CRUD, preview, purchase→sale flow.
- **Frontend tests** — form validation, result rendering, Auction Mode STOP, permission gating.
- **E2E (Playwright)** — the 8-step admin→buyer→purchase→sale→dashboard journey.
