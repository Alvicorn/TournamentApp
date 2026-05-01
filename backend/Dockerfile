FROM python:3.12-slim AS builder
WORKDIR /app

RUN pip install uv
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync --no-dev

FROM python:3.12-slim
WORKDIR /app

COPY --from=builder /app/.venv .venv
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 80

# Run Alembic migrations then start uvicorn
# CMD alembic upgrade head && \
#     uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 2

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--workers", "2"]
