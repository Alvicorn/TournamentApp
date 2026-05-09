"""add backups table

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    backup_trigger = postgresql.ENUM(
        "manual", "pre_action", "hourly", name="backup_trigger", create_type=False
    )
    backup_status = postgresql.ENUM(
        "pending", "complete", "failed", name="backup_status", create_type=False
    )
    backup_trigger.create(op.get_bind(), checkfirst=True)
    backup_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "backups",
        sa.Column("id", sa.UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tournament_id", sa.UUID, sa.ForeignKey("tournaments.id"), nullable=False),
        sa.Column(
            "triggered_by",
            backup_trigger,
            nullable=False,
        ),
        sa.Column("pre_action_description", sa.Text, nullable=True),
        sa.Column("s3_key", sa.Text, nullable=True),
        sa.Column("size_bytes", sa.BigInteger, nullable=True),
        sa.Column(
            "status",
            backup_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("backups")
    op.execute("DROP TYPE IF EXISTS backup_status CASCADE")
    op.execute("DROP TYPE IF EXISTS backup_trigger CASCADE")
