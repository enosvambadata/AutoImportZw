# Architecture

## Monorepo

```
apps/web            Next.js (App Router) + TypeScript + Tailwind
apps/api            FastAPI + SQLAlchemy 2 (async) + Alembic
packages/shared-types   shared TS enums
packages/config         shared tsconfig / eslint base
docs/               documentation
```

Turborepo + pnpm workspaces orchestrate the JS side; the API is a standard Python package.

## Backend layering (`apps/api/app`)

| Layer | Responsibility |
|-------|----------------|
| `calculations/` | Pure Decimal engine (fees, bids, scenarios, sensitivity, ladder). No framework, no DB. |
| `services/` | `risk`, `recommendation`, `evaluation` (combines the three engines), `appraisal_service` (persist + evaluate), `analytics`, `audit`, `csv_import`. |
| `models/` | SQLAlchemy 2 declarative models (16 tables). |
| `schemas/` | Pydantic v2 request/response. |
| `repositories/` | Reserved for heavier query logic; simple queries live in routers scoped by dealership. |
| `integrations/` | Provider interfaces (Protocols) + mock adapters + licensed-provider placeholders. |
| `api/v1/` | FastAPI routers under `/api/v1`. |
| `core/` | config, security (hash/JWT), dependencies (auth + RBAC), rate limiting. |
| `db/` | async engine/session, declarative base + mixins. |

### Request lifecycle

1. Middleware assigns a request ID and sets security headers.
2. `get_current_user` validates the bearer access token; `require_admin` / `require_buyer` enforce RBAC.
3. Routers query with `dealership_id` scoping (multi-tenant isolation).
4. Writes to appraisals call `compute_and_store`, which derives risk signals from the vehicle/history/
   market data, runs `evaluate()` and caches the result columns + `RiskAssessment` row.
5. Sensitive actions append to the audit log.
6. Errors are returned in a structured envelope `{ "error": { code, message, request_id, fields } }`.

## Frontend (`apps/web`)

- App Router with a protected route group `(app)` (client-side auth guard) and a public `/login`.
- A typed `lib/api.ts` client holds the short-lived access token **in memory** and silently refreshes
  it via the HTTP-only cookie on a 401.
- `AuthProvider` bootstraps the session (refresh → `/auth/me`) and exposes `can("write"|"admin")`.
- Money maths is never re-implemented; the wizard calls `/appraisals/preview` and the detail page
  renders the persisted `result_snapshot` through the shared `AppraisalResult` component.

## Data-provider strategy

All third-party data sits behind Protocols in `integrations/base.py`. The MVP ships deterministic
**mock adapters** (`integrations/mock.py`) that seed from the registration string and are labelled
`MOCK_ADAPTER`. Licensed providers (DVLA, DVSA MOT, CAP HPI, Auto Trader, auction feeds) have
documented placeholder adapters wired through `registry.get_providers()`. See
[API_INTEGRATIONS.md](API_INTEGRATIONS.md).

## Why the engine is separate

Keeping the calculation engine free of FastAPI/SQLAlchemy makes it trivially unit-testable and
guarantees a single source of truth. The API exposes it; the frontend consumes it. No duplication.
