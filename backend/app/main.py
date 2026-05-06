"""FastAPI application factory."""

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.routes import (
    activity,
    auth,
    backups,
    divisions,
    health,
    judges,
    matches,
    participants,
    tournaments,
)

log = logging.getLogger(__name__)


async def _hourly_backup_loop() -> None:
    """Background loop: take an hourly backup while a non-demo tournament is active."""
    while True:
        await asyncio.sleep(3600)
        try:
            from sqlalchemy import select

            from app.db import _session_factory
            from app.models.backup import BackupTrigger
            from app.models.tournament import LifecycleState, Tournament
            from app.services.backup import create_backup_record, run_backup

            session_factory = _session_factory()
            db = session_factory()
            try:
                active = db.execute(
                    select(Tournament).where(
                        Tournament.deleted_at.is_(None),
                        Tournament.is_demo.is_(False),
                        Tournament.lifecycle_state == LifecycleState.active,
                    )
                ).scalar_one_or_none()
                if active:
                    b = create_backup_record(db, active.id, triggered_by=BackupTrigger.hourly)
                    db.commit()
                    asyncio.create_task(asyncio.to_thread(run_backup, b.id))
                    log.info("Hourly backup scheduled for tournament %s", active.id)
            finally:
                db.close()
        except Exception:
            log.exception("Hourly backup loop encountered an error")


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    task = asyncio.create_task(_hourly_backup_loop())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


def create_app() -> FastAPI:
    settings = get_settings()
    limiter = Limiter(key_func=get_remote_address)

    app = FastAPI(title="Tournament API", version="0.1.0", lifespan=_lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Phase 1
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1")

    # Phase 2
    app.include_router(tournaments.router, prefix="/api/v1")
    app.include_router(judges.router, prefix="/api/v1")
    app.include_router(participants.router, prefix="/api/v1")
    app.include_router(matches.router, prefix="/api/v1")
    app.include_router(divisions.router, prefix="/api/v1")
    app.include_router(activity.router, prefix="/api/v1")
    app.include_router(backups.router, prefix="/api/v1")

    return app


app = create_app()
