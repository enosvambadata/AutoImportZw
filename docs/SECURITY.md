# Security

## Authentication
- **Passwords** hashed with **Argon2id** (`argon2-cffi`); verification is constant-ish and rehash-aware.
- **Access tokens**: short-lived JWT (default 15 min), `type=access`, carrying `sub`, `role`, `did`.
- **Refresh tokens**: opaque random tokens (48 bytes), **only the SHA-256 hash is stored** server-side
  (`refresh_tokens`). Delivered as an **HTTP-only, SameSite=Lax** cookie scoped to `/api/v1/auth`.
- **Rotation**: each `/auth/refresh` revokes the presented token and issues a new one. Logout revokes
  the active token. Expired/revoked tokens are rejected.
- Access tokens are held **in memory** on the client (never `localStorage`).

## Authorisation (RBAC)
- Enforced **server-side** via dependencies: `require_admin`, `require_buyer`. Hiding a UI button is
  never the control.
- **Viewer** — read-only. **Buyer** — create/edit appraisals, purchases, prep, sales. **Admin** — all,
  plus users, dealership settings and fee schedules.
- Every query is scoped to the caller's `dealership_id`; cross-tenant fetches return 404 (tested in
  `tests/test_api_isolation.py`).

## Transport & headers
- CORS restricted to configured origins with credentials enabled.
- Security headers on every response: `X-Content-Type-Options`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer`, `Permissions-Policy`; **HSTS** when `API_ENV=production`.
- Set `COOKIE_SECURE=true` and serve over HTTPS in production.

## Input & data safety
- All input validated by Pydantic v2; registration/VIN/category formats validated when supplied.
- SQLAlchemy parameterises all queries (no string SQL).
- Errors are sanitised into `{ error: { code, message, request_id, fields } }`; internals never leak.
- Auth endpoints are **rate-limited** (default 10/min/IP, in-process fixed window — swap for Redis in
  production).

## Auditability
- Append-only `audit_logs` capture appraisal create/update, valuation/cost changes, recalculation,
  purchase, sale, settings and role changes, with actor, timestamp, entity and old/new values.

## Secrets
- No secrets in source. `.env.example` documents required variables; generate a strong
  `JWT_SECRET_KEY` (`python -c "import secrets; print(secrets.token_urlsafe(48))"`).

## Known MVP limitations / next steps
- Rate limiter and audit writer are in-process (single instance). Move to Redis / a durable queue.
- Password reset returns a non-committal response and the reset endpoint is a documented stub — wire an
  email provider with signed, single-use tokens.
- Add refresh-token reuse detection (revoke the whole family on replay).
