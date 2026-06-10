# Deployment & Infrastructure

## Stack: Render (free tier) + Supabase + Cloudflare R2

The **frontend is a Render Static Site** and the **backend is a Render Web Service**, with **Supabase** (free tier) for Postgres + admin auth and **Cloudflare R2** (free tier) for backup storage. Total infrastructure cost: **$0/mo**, with a $7/mo Render Starter upgrade path for event months. One vendor for both halves, SSE supported, deploys are a webhook.

There is no Redis and no broker: the backend runs **one instance with one uvicorn worker**, so SSE fan-out and caches are in-process. See [`architecture.md`](architecture.md#single-instance-constraint).

### Free-tier caveats (and how we handle them)

| Caveat | Handling |
|---|---|
| Free Web Services **spin down after 15 min idle**; cold start is ~30–60s | UptimeRobot pings `/health` every 5 min, which keeps the service awake continuously. 750 free instance-hours/mo > hours in a month, so an always-awake single service stays free. |
| 512MB RAM / 0.1 CPU | Fine for FastAPI + a single tournament's load. If event-day load worries you, upgrade to **Starter ($7/mo)** for that month and downgrade after. |
| Supabase free tier **pauses projects after ~1 week of inactivity** | Check the Supabase dashboard days before an event; the UptimeRobot-driven `/health` check also touches the DB, which counts as activity while the Render service is up. |

## Infrastructure

```
┌─ DNS (any provider) ─┐
│                      │
│  tourney.com ────────► Render Static Site (React build, CDN, auto-TLS)
│                      │
│  api.tourney.com ────► Render Web Service (FastAPI, 1 instance, 1 uvicorn worker)
│                           │
│                           ├─► Supabase Postgres (external)
│                           │
│                           └─► Cloudflare R2 (pg_dump backups)
└──────────────────────┘
```

### Custom domain wiring

1. In Render, add `tourney.com` to the static site and `api.tourney.com` to the web service.
2. At your DNS provider, create the CNAME records Render shows you (apex domains use Render's ALIAS/ANAME instructions or an `A` record to Render's IP).
3. Render provisions and renews TLS certificates automatically.

Until DNS is wired, the `*.onrender.com` URLs work; client code always uses the custom domains.

## Components

| Component | Service | Notes |
|---|---|---|
| Frontend hosting | Render Static Site | `pnpm build` → `dist/`; SPA rewrite rule (`/* → /index.html`); CDN + auto-TLS |
| Backend API | Render Web Service | FastAPI; health check path `/health`; **1 instance, 1 uvicorn worker** |
| Database | Supabase | External; free tier viable for MVP |
| Auth (admin) | Supabase Auth | External |
| Backup storage | Cloudflare R2 | 10GB free; S3-compatible API so the `boto3` upload path works with a custom endpoint. Backblaze B2 is an equivalent alternative |
| DNS | Any provider | CNAME → Render |
| TLS | Render-managed | Automatic issue + renew |
| Uptime monitoring | UptimeRobot (free) | 5-min pings on `/health`; doubles as keep-awake; email alert on failure |
| Logs | Render dashboard | Streamed + searchable; no log infrastructure to run |

## Cost estimate

| Item | Monthly |
|---|---|
| Render Web Service (free tier, kept awake by pings) | $0 |
| Render Static Site | $0 |
| Supabase (free tier) | $0 |
| Cloudflare R2 (≤10GB, minimal ops) | $0 |
| UptimeRobot (free plan) | $0 |
| Domain registration | ~$1/mo amortized |
| **Total** | **~$0–1** |

**Event-month upgrade (optional)**: Render Starter at $7/mo removes spin-down behavior entirely and bumps resources. Upgrade a few days before a tournament, downgrade after.

## Application-level resilience

- The backend is a single instance; Render restarts it automatically if it crashes (health check on `/health`).
- A restart drops SSE connections; clients auto-reconnect and re-fetch state (see [`correctness.md`](correctness.md#reconnect-behavior-judges)).
- Public clients poll, so a brief restart shows at most a few seconds of stale data.
- Judges keep scoring through outages anyway — see offline-first scoring in [`correctness.md`](correctness.md#judge-offline-scoring).
- Bad deploys roll back: Render's rolling deploy keeps the previous version serving if the health check fails; one-click rollback in the dashboard.

## Backups

Three-layer strategy. **All backups are automatic** — there's no admin button to push.

1. **Continuous (Supabase free tier)**: daily snapshots, 7-day retention. Disaster floor; restore via Supabase dashboard.
2. **Hourly during active tournaments**: FastAPI background job runs **only while** a tournament has `lifecycle_state = 'active'`. Every hour, `pg_dump` → R2 at `auto/<tournament_id>/<YYYY-MM-DD-HH>.sql.gz`. Retention: 90 days (R2 lifecycle rule). Stops automatically when the tournament completes.
3. **Pre-action snapshots**: server-triggered automatically before risky operations — bracket regeneration, editing a submitted result, lifecycle transitions, late participant additions. Same pipeline, path `pre-action/<tournament_id>/<timestamp>-<action>.sql.gz`, indefinite retention. Visible (read-only) at `/admin/backups`.

**Restore is engineer-only** — never exposed in the admin UI. Restoring overwrites everything since the snapshot; it's a deliberate manual procedure via the Supabase SQL editor (restore to a scratch schema first, verify, then apply).

## Rate limiting

Applied at the FastAPI level via `slowapi`.

**Keying matters**: at a venue, every spectator phone shares the venue Wi-Fi's single public IP. Per-IP limits on public endpoints would throttle legitimate users almost immediately (100 phones × ~20 polls/min = 2,000 req/min from one IP). So:

- **Public read endpoints** are keyed by **`X-Device-Id`** (fallback to IP when the header is absent).
- **Login endpoints** stay keyed **per IP** — the right key for brute-force protection.

| Surface | Key | Limit | Reasoning |
|---|---|---|---|
| Public read endpoints (dashboard, division view, etc.) | device | 60 req/min | Polling = 20/min baseline; 3x headroom |
| Subscriptions endpoints (POST/DELETE) | device | 30 req/min | Prevents subscription spam |
| Admin login | IP | 5 attempts per 15 min | Prevents brute force |
| Judge login | IP | 5 attempts per 15 min | Prevents brute force on codes |
| All other admin endpoints | token subject | 600 req/min | Generous; admin shouldn't hit this |
| All other judge endpoints | token subject | 600 req/min | Score events + offline outbox replay can be rapid; need headroom |
| SSE connection | token subject | 5 concurrent | Prevents connection-bombing |

### Dashboard caching
- The server caches the public dashboard payload **in-process for 3 seconds** and serves all polls from that cache.
- The dashboard response is **device-neutral** (no per-device data baked in); device-specific state like subscriptions comes from separate endpoints.
- 1,000 phones polling every 3s ≈ one real dashboard computation per 3s.

### Response on rate limit hit
- Return `429 Too Many Requests` with `Retry-After` header.
- Client toast: "Too many requests, slowing down…"

## Logging

Render streams stdout/stderr from the FastAPI process; view and search in the Render dashboard.

**INFO**: all admin/judge actions (also in `activity_log`), offline outbox replays (count synced, match id, rejects), tournament lifecycle transitions, SSE connection lifecycle, background job runs (auto-release, backup).

**ERROR**: unhandled exceptions, failed backup uploads, rejected outbox replays (409s with reason — possible lost judge work, deserves review), auth failures (with rate-limit context).

**Never log**: PII beyond already-public participant names, full request bodies on score events (high volume, low value), health-check pings, query strings on `/sse/*` paths (they carry auth tokens).

## Tournament lifecycle behavior

Server behavior on each transition (the admin UI triggers these with confirmation modals):

### `setup → active` ("Start Tournament")
- Pre-flight check: ≥1 division with ≥2 participants; block with a clear error otherwise.
- Custom field spec freezes.
- Hourly backup job starts.
- Activity log: `tournament.activated`.

### `active → completed` ("Complete Tournament")
- Pre-flight check: all divisions `completed`, or admin acknowledges incomplete divisions.
- Hourly backup job stops; final snapshot taken automatically.
- Public view becomes read-only (URLs keep working indefinitely).
- Subscribers receive a tournament-wide "Tournament complete" notification (non-personalized).
- Activity log: `tournament.completed`.

### `active → setup` (emergency revert)
- Hard warning modal; type `REVERT` to confirm. Unfreezes the custom field spec (may affect existing participant data).
- Hourly backup job stops.
- Activity log: `tournament.reverted_to_setup`.

## CI/CD

GitHub Actions. Deploys are gated on tests and triggered via **Render deploy hooks** (secret webhook URLs stored as repo secrets: `RENDER_DEPLOY_HOOK_BACKEND`, `RENDER_DEPLOY_HOOK_FRONTEND`). Auto-deploy-on-push is disabled in Render so nothing deploys without green CI.

### Frontend
1. Install deps, run lint + tests + type check.
2. `curl -fsS "$RENDER_DEPLOY_HOOK_FRONTEND"` — Render pulls the repo, runs `pnpm build`, publishes `dist/`.

### Backend
1. Install deps, run lint + tests + type check.
2. `curl -fsS "$RENDER_DEPLOY_HOOK_BACKEND"` — Render builds and rolls out with the `/health` check; a failing deploy keeps the previous version serving.

A `render.yaml` blueprint at the repo root declares both services so the setup is reproducible.

> Build-time frontend env (`VITE_API_URL`, `VITE_VAPID_PUBLIC_KEY`) is configured as environment variables on the Render static site, not in CI.

## Environment configuration

| Variable | Where | Notes |
|---|---|---|
| `DATABASE_URL` | Render web service env | Supabase connection string |
| `SUPABASE_URL`, `SUPABASE_KEY` | Render web service env | Health check + JWKS derivation |
| `JUDGE_JWT_SECRET` | Render web service env | HS256 secret for judge tokens |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` | Render web service env | Web push |
| `ADMIN_EMAIL_ALLOWLIST` | Render web service env | Comma-separated list |
| `BACKUP_S3_BUCKET` | Render web service env | R2 bucket name (S3-compatible) |
| `BACKUP_S3_ENDPOINT_URL` | Render web service env | R2 endpoint, e.g. `https://<account>.r2.cloudflarestorage.com` |
| `BACKUP_S3_ACCESS_KEY_ID`, `BACKUP_S3_SECRET_ACCESS_KEY` | Render web service env | R2 API token credentials |
| `VITE_API_URL` | Render static site env | Baked into frontend build |
| `VITE_VAPID_PUBLIC_KEY` | Render static site env | Baked into frontend build |

`.env.example` files in `backend/` and `frontend/` mirror these for local development.

## Future infrastructure work

- Reintroduce a cross-worker pub/sub broker (Postgres `LISTEN/NOTIFY` or managed Redis) only if a single instance ever becomes a real bottleneck.
- Move Postgres from Supabase to a paid tier or another managed Postgres if free-tier limits bite.
- Add proper observability (Sentry, structured metrics) — currently Render logs + UptimeRobot only.
- Cloudflare in front of the API for edge caching if public polling load ever exceeds what the in-process cache absorbs.
