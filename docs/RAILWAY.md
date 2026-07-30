# Deploying to Railway

This monorepo runs as **three Railway services** in one project: **Postgres** (plugin), **api**
(FastAPI, root `apps/api`), and **web** (Next.js, root `apps/web`). You can reuse the existing project
that currently hosts "vamba collect" — add the services below and retire the old one.

> **Before you start:** rotate the Railway token you shared earlier, then `railway login` locally (or
> use the dashboard). Generate a strong JWT secret: `openssl rand -hex 32`.

---

## 0. Push the repo to GitHub
Rotate your GitHub PAT first, then:
```
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```
Railway deploys from this GitHub repo.

## 1. Postgres
In the project → **New → Database → PostgreSQL**. It exposes `DATABASE_URL`. The app auto-adds the
`+asyncpg` / `+psycopg` drivers, so you pass the plain URL as-is.

## 2. api service (deploy this FIRST)
- **New → GitHub Repo → this repo**, then **Settings → Root Directory = `apps/api`** (it picks up
  `apps/api/railway.json` + Dockerfile automatically; migrations run on boot).
- **Add a Volume** mounted at `/data/media` (persists uploaded car photos).
- **Variables:**
  ```
  DATABASE_URL       = ${{Postgres.DATABASE_URL}}
  JWT_SECRET_KEY     = <output of: openssl rand -hex 32>
  API_ENV            = production
  COOKIE_SECURE      = true
  MEDIA_DIR          = /data/media
  MEDIA_BASE_URL     = https://<api-domain>        # set after you generate the domain below
  CORS_ORIGINS       = https://<web-domain>         # set after the web service exists
  DVSA_MOT_API_KEY / DVSA_MOT_CLIENT_ID / DVSA_MOT_CLIENT_SECRET / DVSA_MOT_TOKEN_URL   # your live MOT creds
  EBAY_CLIENT_ID / EBAY_CLIENT_SECRET               # optional (parts)
  ANTHROPIC_API_KEY                                 # optional (turns on real Claude parsing/damage)
  ```
- **Settings → Networking → Generate Domain.** Copy it → set `MEDIA_BASE_URL` to `https://<that>`.
  (The API guard will refuse to boot if `JWT_SECRET_KEY` is the default — that's intentional.)

## 3. web service (deploy SECOND)
- **New → GitHub Repo → same repo**, **Root Directory = `apps/web`**.
- **Variables** (these are baked in at build — a redeploy is needed if you change them):
  ```
  NEXT_PUBLIC_API_BASE_URL = https://<api-domain>/api/v1
  NEXT_PUBLIC_WHATSAPP     = +263...                # your WhatsApp number
  ```
- **Generate Domain.** Copy `https://<web-domain>`.

## 4. Close the loop
- Back on **api → Variables**, set `CORS_ORIGINS = https://<web-domain>` and redeploy api.
- Redeploy web if you changed the API domain after its first build.

## 5. Verify
- `https://<api-domain>/health` → `{"status":"ok"}`
- `https://<web-domain>/store` → the storefront
- Log in to the admin at `https://<web-domain>/login` (seed creates demo users on first boot — change
  or wipe them: the API container ran `python -m app.seed --if-empty`).

---

## Notes & gotchas
- **Order matters** because of the build-time API URL and the cross-service CORS/MEDIA URLs. Deploy
  **api → web → set CORS on api**.
- **Photos**: uploads persist only because of the `/data/media` **volume** — don't skip it.
- **Migrations** run automatically (`alembic upgrade head`) on every api deploy.
- **Custom domain**: add it under each service's Networking, then update `CORS_ORIGINS`,
  `MEDIA_BASE_URL`, and `NEXT_PUBLIC_API_BASE_URL` to the custom hostnames and redeploy.
- **Secrets** live only in Railway variables (and your local git-ignored `.env`) — never in the repo.
