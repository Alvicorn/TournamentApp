# Tournament App

A web app for monitoring a live martial arts tournament. See [`docs/`](docs/) for the full spec.

## Layout

```
backend/    FastAPI + SQLAlchemy + Alembic
frontend/   React + TypeScript + Vite + Zustand + Tailwind
.github/    CI/CD workflows (deploys via Render deploy hooks)
render.yaml Render blueprint (web service + static site)
docs/       Source of truth — read this first
```

Hosting: Render (frontend static site + backend web service), Supabase (Postgres + admin auth). See [`docs/deployment.md`](docs/deployment.md).

## Local development

### Backend
```bash
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
pnpm install
pnpm dev
```

### Tests
```bash
# Backend
cd backend && uv run pytest

# Frontend
cd frontend && pnpm test
```

## Environment

Copy `.env.example` files in `backend/` and `frontend/` and fill in. See [`docs/deployment.md`](docs/deployment.md#environment-configuration).
