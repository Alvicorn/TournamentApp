# Architecture

## High-level topology

```
┌─ DNS (any provider, CNAME records) ─┐
│                                     │
│  tourney.com ──────► Render Static Site (React build, CDN, auto-TLS)
│                                     │
│  api.tourney.com ──► Render Web Service (FastAPI container, 1 instance, 1 worker)
│                          │
│                          ├─► Supabase Postgres (external, free tier)
│                          │
│                          └─► Cloudflare R2 (pg_dump backups, S3-compatible)
└─────────────────────────────────────┘
```

**Data flow**: `React → FastAPI → SQLAlchemy → Supabase Postgres`. **Frontend never talks to Supabase directly** (and never uses the Supabase client SDK) — all business logic, auth checks, mutations, and SSE fan-out live in FastAPI: one enforcement point, one audit trail, one API surface to test.

See [`deployment.md`](deployment.md) for the full deployment story.

## Single-instance constraint

The backend runs as **one Render instance with one uvicorn worker**. This is a deliberate simplification:

- SSE fan-out needs no external broker — an **in-process asyncio pub/sub** bus reaches every connected SSE client because they all live in the same process.
- The standings cache and the 3-second dashboard cache are plain in-process dicts with TTL.
- No Redis, no EC2, no Terraform, no cross-worker coordination.

At this app's scale (one active tournament, a handful of judges/admins on SSE, public viewers on polling against a cached response) a single small instance is plenty.

**Escape hatch if we ever outgrow it**: reintroduce a broker for cross-worker fan-out — Postgres `LISTEN/NOTIFY` (already have Postgres) or a managed Redis. The pub/sub bus is behind a small interface so only that module changes. This is future work; do not build it speculatively.

## Realtime strategy

| Surface | Mechanism | Reasoning |
|---|---|---|
| Public dashboard / slideshow / division view | **Polling every 3–5s** | Highest viewer count; server returns an in-process 3s-TTL cached payload, so polls are nearly free |
| Judge scoring screen | **SSE** | Low audience, sub-second updates required |
| Admin division view | **SSE** | Few admins, near-realtime needed |
| Admin lists (judges, participants) | **No realtime** | Manual refresh fine |
| Web Push (tab closed) | **VAPID** | Subscriber notifications when not in app |

**SSE fan-out**: events published by request handlers go onto the in-process asyncio bus; subscriber tasks (one per SSE connection) receive them directly. See the single-instance constraint above.

**SSE auth**: `EventSource` cannot set an `Authorization` header. SSE endpoints accept the JWT as a `?token=` query parameter instead; same verification path as header auth. Tokens in URLs are acceptable here because SSE URLs are never shared/bookmarked and access logs must not log query strings on `/sse/*`.

## Offline-first judge scoring

Judges keep scoring even when their device loses network mid-match. Score taps and round-control actions are queued in a client-side outbox and replayed (idempotently, with client-captured timestamps) when connectivity returns. The full design lives in [`correctness.md`](correctness.md#judge-offline-scoring); the UX in [`frontend.md`](frontend.md#judge-offline-banner).

## Authentication flow

```
Admin:   React → Supabase Auth (login) → JWT → React → FastAPI (verifies JWT)
Judge:   React → FastAPI (login w/ code) → FastAPI-signed JWT → React → FastAPI
Public:  React generates UUID → stored in localStorage → sent as X-Device-Id header
```

## Components

| Component | Tech | Where it lives |
|---|---|---|
| Web app | React + TS + Tailwind + Zustand | Render Static Site (CDN) |
| API | FastAPI + SQLAlchemy + Alembic | Render Web Service (single instance) |
| Database | Postgres | Supabase (external) |
| Auth (admin) | Supabase Auth | Supabase (external) |
| Realtime fan-out | In-process asyncio pub/sub | Inside the FastAPI process |
| Backups | `pg_dump` → Cloudflare R2 | R2 bucket (S3-compatible API) |
| DNS | Any provider (CNAME → Render) | — |
| TLS | Render-managed | — |
| Uptime monitoring | UptimeRobot (free) | External, pings `/health` |
| Web push | VAPID + Service Worker | Browser + FastAPI |
