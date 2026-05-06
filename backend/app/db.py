from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from supabase import Client, create_client

from app.config import get_settings

_settings = get_settings()

# ---------------------------------------------------------------------------
# Supabase client (Phase 1 — kept for auth proxy)
# ---------------------------------------------------------------------------
supabase: Client = create_client(_settings.supabase_url, _settings.supabase_key)


# ---------------------------------------------------------------------------
# SQLAlchemy (sync) — used by all Phase 2+ services
# ---------------------------------------------------------------------------


@lru_cache
def _engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, echo=False)


@lru_cache
def _session_factory() -> sessionmaker:  # type: ignore[type-arg]
    return sessionmaker(bind=_engine(), autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session, rolls back on error."""
    factory = _session_factory()
    db: Session = factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
