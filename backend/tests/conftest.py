"""Shared pytest fixtures for backend tests.

Provides:
- A session-scoped Postgres container (Testcontainers)
- A session-scoped SQLAlchemy engine with all tables created
- A function-scoped DB session wrapped in a rolled-back transaction
- A FastAPI TestClient with get_db and require_admin overridden
"""

import os

# Set minimal env vars before importing app modules
# These must be set BEFORE importing app.db and other modules that create clients
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.test"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.postgres import PostgresContainer

from app.auth.dependencies import AdminPrincipal, require_admin
from app.db import get_db
from app.main import create_app


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def test_engine(postgres_container):
    # testcontainers returns a psycopg2-style URL; swap to psycopg (v3)
    url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+psycopg://"
    )
    engine = create_engine(url, echo=False)
    with engine.connect() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        conn.commit()
    # Import models package so all ORM classes register with Base.metadata
    from app.models import Base  # noqa: F401

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session(test_engine) -> Session:
    """Each test gets its own transaction; rolled back after the test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session_local = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session: Session = session_local()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    """TestClient with DB and admin-auth dependencies overridden."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[require_admin] = lambda: AdminPrincipal(
        role="admin", user_id="00000000-0000-0000-0000-000000000001", email="admin@test.com"
    )
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
