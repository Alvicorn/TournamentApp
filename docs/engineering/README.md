# Engineering

How the app is built — code-level documentation for backend, frontend, and the correctness-critical edges.

## Files

- **[`architecture.md`](architecture.md)** — High-level system shape, data flow, realtime strategy.
- **[`backend.md`](backend.md)** — FastAPI service, data model (full schema), API surface, concurrency safety, rate limiting.
- **[`frontend.md`](frontend.md)** — React app, routes, Zustand stores, UX guardrails for all three roles.
- **[`correctness.md`](correctness.md)** — Edge cases that bite if missed: timer authority, idempotency, reconnect, race conditions, audit trails.

## When to update files here

- New API route → `backend.md`
- New frontend route or UX pattern → `frontend.md`
- Schema change → `backend.md`
- New edge case discovered → `correctness.md` and append a gotcha to [`../process/memory.md`](../process/memory.md)
- Architecture-level change → `architecture.md` and probably also `backend.md` / `frontend.md`

If a change here is driven by a product decision, update [`../product/`](../product/) first.
