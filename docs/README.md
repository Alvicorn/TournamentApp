# Project: Martial Arts Tournament Monitoring App

This directory is the **single source of truth** for the project. Files are organized into four subdirectories by concern.

## Directory layout

```
.claude/
├── README.md
├── product/                   ← what we're building and why
│   ├── overview.md
│   ├── user-stories.md
│   └── rules.md
├── engineering/               ← how it's built
│   ├── architecture.md
│   ├── backend.md
│   ├── frontend.md
│   └── correctness.md
├── infra/                     ← how it runs
│   ├── deployment.md
│   └── operations.md
└── process/                   ← how we work on it
    ├── testing.md
    ├── backlog.md
    └── memory.md
```

## Reading order

If you're new, read in this order:

| # | File | Why first |
|---|------|-----------|
| 1 | [`product/overview.md`](product/overview.md) | What the app is, who uses it |
| 2 | [`product/user-stories.md`](product/user-stories.md) | Scope and roles |
| 3 | [`product/rules.md`](product/rules.md) | Tournament logic — the domain |
| 4 | [`engineering/architecture.md`](engineering/architecture.md) | High-level system shape |
| 5 | [`engineering/backend.md`](engineering/backend.md) | FastAPI, data model, APIs |
| 6 | [`engineering/frontend.md`](engineering/frontend.md) | React, routes, UX |
| 7 | [`engineering/correctness.md`](engineering/correctness.md) | Edge cases that bite if missed |
| 8 | [`process/testing.md`](process/testing.md) | How we verify it works |
| 9 | [`infra/deployment.md`](infra/deployment.md) | AWS topology, CI/CD |
| 10 | [`infra/operations.md`](infra/operations.md) | Backups, monitoring, runbooks |
| 11 | [`process/backlog.md`](process/backlog.md) | Phased plan + future work |
| 12 | [`process/memory.md`](process/memory.md) | Decision log, gotchas — read last, refer to often |

## What goes where

- **`product/`** — anything a non-engineer should be able to read. The "what" and "why" of the app.
- **`engineering/`** — the "how" at the code level. Frontend, backend, data model, edge-case behavior.
- **`infra/`** — the "where" the app runs. AWS resources, deployment, operations runbooks.
- **`process/`** — meta-concerns. Testing strategy, what's pending, history of decisions.

## Working with this directory

- **When a decision is made**, update the relevant file. Do not silently override.
- **When you discover a gotcha**, append it to [`process/memory.md`](process/memory.md).
- **When scope changes**, update [`process/backlog.md`](process/backlog.md) first; the rest of the docs follow.
- **Cross-reference, don't duplicate**: if rules are in `product/rules.md`, link to that section from elsewhere.
- **When adding a new doc**, place it in the most appropriate subdirectory and update this README's directory layout + reading order.

## Quick reference

| Need | Look here |
|------|-----------|
| What does this app do? | [`product/overview.md`](product/overview.md) |
| What are the tournament rules? | [`product/rules.md`](product/rules.md) |
| What's the data model? | [`engineering/backend.md`](engineering/backend.md) |
| What's a route called X? | [`engineering/backend.md`](engineering/backend.md) (API) or [`engineering/frontend.md`](engineering/frontend.md) (UI) |
| What if X edge case happens? | [`engineering/correctness.md`](engineering/correctness.md) |
| How does it deploy? | [`infra/deployment.md`](infra/deployment.md) |
| Something broke at the venue — what do I do? | [`infra/operations.md`](infra/operations.md) (runbooks) |
| Why was X decided that way? | [`process/memory.md`](process/memory.md) |
| What's next to build? | [`process/backlog.md`](process/backlog.md) |
| How do we test this? | [`process/testing.md`](process/testing.md) |
