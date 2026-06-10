# Project: Martial Arts Tournament Monitoring App

This directory is the **single source of truth** for the project. Flat structure, ten files.

## Files & reading order

| # | File | What's in it |
|---|------|--------------|
| 1 | [`product.md`](product.md) | What the app is, who uses it, scope (user stories), tournament rules, state machines |
| 2 | [`architecture.md`](architecture.md) | System shape, data flow, single-instance constraint, realtime strategy, auth flows |
| 3 | [`backend.md`](backend.md) | FastAPI service: full data model, API surface, background jobs, concurrency safety |
| 4 | [`frontend.md`](frontend.md) | React app: routes, stores, UX guardrails, offline UX, empty states |
| 5 | [`correctness.md`](correctness.md) | Edge cases that bite if missed: timer authority, idempotency, offline scoring, races |
| 6 | [`testing.md`](testing.md) | Test layers, BDD scope, simulation suite, CI pipeline, coverage targets |
| 7 | [`deployment.md`](deployment.md) | Hosting (Render/Supabase/R2), backups, rate limiting, logging, lifecycle behavior, CI/CD |
| 8 | [`backlog.md`](backlog.md) | Phased implementation plan, open design questions, future work, known limitations |
| 9 | [`conventions.md`](conventions.md) | Naming conventions + one-page gotcha cheat sheet — refer to it often |

## Working with this directory

- **When a decision is made or changed**, update the relevant file. Docs describe current state only — no history, no "previously we did X".
- **Cross-reference, don't duplicate**: if a rule lives in `product.md`, link to it from elsewhere.
- **New gotcha discovered** → add it to [`conventions.md`](conventions.md).
- **Scope changes** → update [`backlog.md`](backlog.md) first; the rest of the docs follow.

## Quick reference

| Need | Look here |
|------|-----------|
| What does this app do? What are the rules? | [`product.md`](product.md) |
| What's the data model / a route called X? | [`backend.md`](backend.md) (API) or [`frontend.md`](frontend.md) (UI) |
| What if X edge case happens? | [`correctness.md`](correctness.md) |
| How does offline judge scoring work? | [`correctness.md`](correctness.md#judge-offline-scoring) |
| How does it deploy? What are the env vars? | [`deployment.md`](deployment.md) |
| What's next to build? What's still undecided? | [`backlog.md`](backlog.md) |
| How do we test this? | [`testing.md`](testing.md) |
| Naming / things that are easy to get wrong | [`conventions.md`](conventions.md) |
