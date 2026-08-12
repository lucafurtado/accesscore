# Deploying AccessCore (R$0 / $0 cost)

Architecture: **Vercel** (frontend) + **Render** (backend, Docker) + **Neon** (Postgres). All three have permanent free tiers that don't require a credit card for the tiers used here (verified against each provider's official docs in August 2026 — pricing changes, so re-verify if this is stale).

**Live instances** (deployed 2026-08-12):
- Frontend: https://accesscore-ten.vercel.app
- Backend: https://accesscore-backend.onrender.com
- API docs: https://accesscore-backend.onrender.com/docs

The steps below are the *intended* dashboard-driven path. Three things behaved differently in practice on Render's Free plan — each is called out inline, with what was actually done instead.

## 1. Database — Neon

1. Sign up at [neon.tech](https://neon.tech) (GitHub OAuth is fastest). No credit card required for the Free plan.
2. Create a project (any name/region). Neon creates a default database and gives you a connection string immediately.
3. Copy the **pooled connection string** shown in the dashboard. It looks like:
   ```
   postgresql://<user>:<password>@<host>/<dbname>?sslmode=require
   ```
4. AccessCore uses SQLAlchemy's async driver, so the URL needs the `+asyncpg` dialect marker. Rewrite it to:
   ```
   postgresql+asyncpg://<user>:<password>@<host>/<dbname>?ssl=require
   ```
   (note: `sslmode=require` → `ssl=require` — asyncpg's query param spelling differs from the standard `libpq` one)
5. Keep this connection string handy for step 2 below — you'll paste it directly into Render's dashboard, not into any file in this repo.

## 2. Backend — Render

1. Sign up at [render.com](https://render.com), connect your GitHub account, and authorize access to this repository.
2. **New > Web Service** → select this repo.
3. Configure:
   | Field | Value |
   |---|---|
   | Runtime | Docker |
   | Root Directory | `backend` |
   | Dockerfile Path | `backend/Dockerfile.prod` |
   | Plan | Free |
   | Health Check Path | `/health` |
   | Pre-Deploy Command | `alembic upgrade head` |
4. Environment variables (Render dashboard → Environment):
   | Key | Value |
   |---|---|
   | `DATABASE_URL` | the Neon connection string from step 1 (with `+asyncpg`) |
   | `JWT_SECRET_KEY` | generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
   | `CORS_ORIGINS` | `["https://<your-vercel-app>.vercel.app"]` — fill in after step 3 |
   | `DEBUG` | `false` |
   | `ENABLE_API_DOCS` | `true` (shows `/docs` and `/redoc` publicly — deliberate for a portfolio project) |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` |
   | `REFRESH_TOKEN_EXPIRE_DAYS` | `7` |
   | `BCRYPT_ROUNDS` | `12` |
5. Deploy. Render builds the Docker image and starts the service.
6. **Known limitation**: the free plan sleeps after 15 minutes of inactivity; the first request after that takes ~30-60s to cold-start. This is expected and documented in the README, not a bug.
7. Once live, verify: `curl https://<your-service>.onrender.com/health` should return `{"status":"ok","database":"up"}`.

### What actually differed on Free plan (found during the real deploy)

1. **The Pre-Deploy Command silently does not run on the Free plan.** It's accepted by the dashboard/API and stored on the service with no error, but no `pre_deploy` event ever appears in the service's event log, and the first deploy left the database with zero tables despite the command being configured. Confirmed empirically, not documented explicitly by Render at the time of writing. **What to do instead**: run migrations out-of-band via `.github/workflows/migrate.yml` — a manually-triggered (`workflow_dispatch`) GitHub Actions job that runs `alembic upgrade head` against `secrets.PRODUCTION_DATABASE_URL`. Trigger it once after the first deploy, and again after every future migration:
   ```bash
   gh workflow run migrate.yml
   ```
   This also means app deploys and schema migrations are decoupled — a schema change only reaches production when someone deliberately runs this workflow, independent of when the app code auto-deploys.

2. **One-off Jobs (`POST /v1/services/{id}/jobs`) are rejected on Free plan** (`"new paid services not allowed"`), so the dashboard's "Shell → run `python -m app.db.seed`" instruction above doesn't work either without upgrading. **What to do instead**: run the seed script from any machine with network access to Neon, pointing `DATABASE_URL` directly at the production database:
   ```bash
   DATABASE_URL="<neon connection string, +asyncpg>" \
   JWT_SECRET_KEY="<same value configured on Render>" \
   SEED_ADMIN_EMAIL="admin@accesscore.dev" \
   SEED_ADMIN_PASSWORD="<a real password>" \
   python -m app.db.seed
   ```
   Then remove `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD` from wherever you set them — never leave them set anywhere in production.

3. **A service created via the Render REST API (rather than through the dashboard's "New > Web Service" GitHub-connect flow) does not get the GitHub webhook that drives auto-deploy-on-push**, even with `autoDeploy: "yes"` set on the service. Pushes to `main` do not trigger a new deploy automatically in that case. **What to do instead**: either connect the repo through the dashboard once (Render dashboard → service → Settings → verify a GitHub connection exists — this wires up the webhook retroactively), or trigger deploys manually after each push:
   ```bash
   curl -X POST -H "Authorization: Bearer $RENDER_API_KEY" \
     "https://api.render.com/v1/services/$SERVICE_ID/deploys"
   ```
   This repo's live instance was provisioned via the API (see the git history around the Milestone 5 deploy commits) and currently requires the manual trigger above until the dashboard connection is made.

## 3. Frontend — Vercel

From the `frontend/` directory, with the Vercel CLI authenticated:

```bash
vercel link       # first time: creates/links the project
vercel env add NEXT_PUBLIC_API_BASE_URL production   # https://<your-service>.onrender.com/api/v1
vercel env add BACKEND_API_URL production              # same value
vercel --prod
```

Then go back to Render and set `CORS_ORIGINS` to the real `https://<project>.vercel.app` URL Vercel gives you, and redeploy the backend so CORS allows it.

## 4. Post-deploy checklist

- [ ] `GET /health` on the backend returns 200 with `"database": "up"`
- [ ] `/login` on the frontend loads and can authenticate against the deployed backend
- [ ] `/dashboard` shows real data (not zeros/placeholders)
- [ ] A restricted (non-admin) login shows a reduced UI and the backend independently rejects the same restricted actions via direct API calls
- [ ] `/docs` is reachable on the backend and does not leak secrets
- [ ] Audit log entries appear for actions taken during this checklist

## Cost

Every service used here has a genuinely free, permanent tier (not a trial) as of the date this was written: Neon Free (0.5GB, scales to zero when idle), Render Free (750 instance-hours/month, sleeps after 15 min idle), Vercel Hobby (100GB transfer/month). **Expected monthly cost: $0.** The main practical trade-off is the Render cold start after idle — acceptable for a portfolio demo, not acceptable for a real production SLA.
