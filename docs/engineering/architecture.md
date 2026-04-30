# Architecture

## High-level topology

```
┌─ Route 53 ─┐
│            │
│  tourney   │
│  .com      │
│            │
└──┬──────┬──┘
   │      │
   │      └────► CloudFront ────► S3 (React static build)
   │
   └─ api.tourney.com ──► ALB (provisioned by ECS Express Mode)
                          │
                          └─► Fargate task: FastAPI container
                                 │
                                 ├─► EC2 t4g.nano (Redis container, hardened)  [SSE pub/sub fan-out]
                                 │      same VPC
                                 │
                                 └─► Supabase Postgres (external)
```

**Data flow**: `React → FastAPI → SQLAlchemy → Supabase Postgres`. Frontend never talks to Supabase directly.

See [`deployment.md`](../infra/deployment.md) for the full deployment story.

## Realtime strategy

| Surface | Mechanism | Reasoning |
|---|---|---|
| Public dashboard / slideshow / division view | **Polling every 3–5s** | Highest viewer count; SSE concurrency cost too high |
| Judge scoring screen | **SSE** | Low audience, sub-second updates required |
| Admin division view | **SSE** | Few admins, near-realtime needed |
| Admin lists (judges, participants) | **No realtime** | Manual refresh fine |
| Web Push (tab closed) | **VAPID** | Subscriber notifications when not in app |

**SSE fan-out**: FastAPI runs with multiple uvicorn workers. Workers publish events to **Redis pub/sub**, and each worker fans events out to its connected SSE clients. Without Redis, an event published in worker A would never reach SSE clients connected to worker B.

## Authentication flow

```
Admin:   React → Supabase Auth (login) → JWT → React → FastAPI (verifies JWT)
Judge:   React → FastAPI (login w/ code) → FastAPI-signed JWT → React → FastAPI
Public:  React generates UUID → stored in localStorage → sent as X-Device-Id header
```

## Why not Supabase client SDK?

We could've had React talk to Supabase directly, but we chose a strict `React → FastAPI → SQLAlchemy → Postgres` flow. Reasons:

- Single source of truth for business logic (all rules enforced in FastAPI).
- Cleaner audit trail (every mutation passes through one layer).
- Easier to test (mock one API surface, not two).
- SSE fan-out lives in FastAPI, not split across two systems.

Trade-off: we lose Supabase Realtime out-of-the-box, hence the Redis pub/sub solution above.

## Components

| Component | Tech | Where it lives |
|---|---|---|
| Web app | React + TS + Tailwind + Zustand | S3 + CloudFront |
| API | FastAPI + SQLAlchemy + Alembic | ECS Express Mode (Fargate) |
| Database | Postgres | Supabase (external) |
| Auth (admin) | Supabase Auth | Supabase (external) |
| Realtime fan-out | Redis pub/sub | EC2 t4g.nano (hardened) |
| Static assets | React build artifacts | S3 |
| CDN | CloudFront | AWS edge |
| DNS | Route 53 | AWS |
| Web push | VAPID + Service Worker | Browser + FastAPI |
