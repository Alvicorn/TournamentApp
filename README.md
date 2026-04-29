# Tournament App

A web app for monitoring a live martial arts tournament. See [`docs/`](docs/) for the full spec.

## Layout

```
backend/    FastAPI + SQLAlchemy + Alembic
frontend/   React + TypeScript + Vite + Zustand + Tailwind
infra/      Terraform for Redis EC2 + CloudWatch
.github/    CI/CD workflows
docs/       Source of truth — read this first
```

## Local development

### Backend
```bash
cd backend
uv sync
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

Copy `.env.example` files in `backend/` and `frontend/` and fill in. See [`docs/infra/deployment.md`](docs/infra/deployment.md#environment-configuration).
