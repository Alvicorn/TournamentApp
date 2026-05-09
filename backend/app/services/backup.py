"""Backup service — pg_dump + S3 upload.

BackgroundTasks-compatible: run_backup() opens its own DB session since it
runs outside the request lifecycle.
"""

import gzip
import logging
import os
import subprocess
import tempfile
import urllib.parse
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.backup import Backup, BackupStatus, BackupTrigger

log = logging.getLogger(__name__)


def create_backup_record(
    db: Session,
    tournament_id: UUID,
    triggered_by: BackupTrigger,
    pre_action_description: str | None = None,
) -> Backup:
    """Insert a pending backup row and return it. Caller must commit."""
    b = Backup(
        tournament_id=tournament_id,
        triggered_by=triggered_by,
        pre_action_description=pre_action_description,
        status=BackupStatus.pending,
    )
    db.add(b)
    db.flush()
    return b


def run_backup(backup_id: UUID) -> None:
    """Background task: pg_dump → gzip → S3. Opens its own DB session."""
    from app.config import get_settings
    from app.db import _session_factory

    settings = get_settings()
    session_factory = _session_factory()
    db: Session = session_factory()

    try:
        backup = db.execute(select(Backup).where(Backup.id == backup_id)).scalar_one_or_none()
        if backup is None:
            log.error("Backup record %s not found", backup_id)
            return

        with tempfile.NamedTemporaryFile(suffix=".sql.gz", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)

        try:
            parsed = urllib.parse.urlparse(settings.database_url)
            pg_env = {**os.environ, "PGPASSWORD": parsed.password or ""}
            pg_args = ["pg_dump"]
            if parsed.hostname:
                pg_args += ["-h", parsed.hostname]
            if parsed.port:
                pg_args += ["-p", str(parsed.port)]
            if parsed.username:
                pg_args += ["-U", parsed.username]
            if parsed.path and parsed.path.lstrip("/"):
                pg_args += ["-d", parsed.path.lstrip("/")]

            result = subprocess.run(
                pg_args,
                capture_output=True,
                timeout=300,
                env=pg_env,
            )
            if result.returncode != 0:
                log.error("pg_dump failed: %s", result.stderr.decode())
                backup.status = BackupStatus.failed
                db.commit()
                return

            with gzip.open(tmp_path, "wb") as gz:
                gz.write(result.stdout)

            s3_key = f"backups/{backup.tournament_id}/{backup_id}.sql.gz"

            import boto3  # type: ignore[import-untyped]

            s3 = boto3.client(
                "s3",
                region_name=settings.s3_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
            s3.upload_file(str(tmp_path), settings.s3_bucket, s3_key)

            backup.s3_key = s3_key
            backup.size_bytes = tmp_path.stat().st_size
            backup.status = BackupStatus.complete
            from sqlalchemy import text

            db.execute(
                text("UPDATE backups SET completed_at = now() WHERE id = :id"),
                {"id": backup_id},
            )
            db.commit()
            log.info("Backup %s complete: %s (%d bytes)", backup_id, s3_key, backup.size_bytes)

        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    except Exception:
        log.exception("Backup %s failed with unexpected error", backup_id)
        try:
            backup.status = BackupStatus.failed  # type: ignore[union-attr]
            db.commit()
        except Exception:
            pass
    finally:
        db.close()
