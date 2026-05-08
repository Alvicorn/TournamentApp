"""Backup routes."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser
from app.db import get_db
from app.models.backup import Backup, BackupTrigger
from app.schemas.backup import BackupOut
from app.services.backup import create_backup_record, run_backup
from app.services.tournament import get_tournament_or_404

router = APIRouter(tags=["backups"])


@router.get("/tournaments/{tournament_id}/backups", response_model=list[BackupOut])
def list_backups(
    tournament_id: UUID,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> list[BackupOut]:
    get_tournament_or_404(db, tournament_id)
    rows = db.execute(
        select(Backup)
        .where(Backup.tournament_id == tournament_id)
        .order_by(Backup.created_at.desc())
    ).scalars()
    return list(rows)  # type: ignore[arg-type]


@router.post(
    "/tournaments/{tournament_id}/backups",
    status_code=status.HTTP_201_CREATED,
    response_model=BackupOut,
)
def create_backup(
    tournament_id: UUID,
    admin: AdminUser,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),  # noqa: B008
) -> BackupOut:
    get_tournament_or_404(db, tournament_id)
    b = create_backup_record(db, tournament_id, triggered_by=BackupTrigger.manual)
    db.commit()
    background_tasks.add_task(run_backup, b.id)
    db.refresh(b)
    return b  # type: ignore[return-value]
