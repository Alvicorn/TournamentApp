# Infrastructure & Operations

How and where the app runs. AWS resources, deployment topology, backups, monitoring, and runbooks for when things break.

## Files

- **[`deployment.md`](deployment.md)** — AWS topology, CI/CD, Redis hardening, environment variables, cost breakdown.
- **[`operations.md`](operations.md)** — Backups (3-layer), monitoring, rate limiting tables, pre-tournament checklist, runbooks for incidents.

## When to update files here

- AWS resource added/changed → `deployment.md`
- New environment variable → `deployment.md`
- New incident scenario observed → `operations.md` (add a runbook)
- Backup or monitoring policy change → `operations.md`
- Tournament-day procedure change → `operations.md` (pre-tournament checklist)

The pre-tournament checklist in [`operations.md`](operations.md#pre-tournament-checklist) is the most important file in this directory. Keep it accurate.
