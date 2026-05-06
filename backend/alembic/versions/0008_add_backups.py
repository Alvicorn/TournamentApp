"""add backups table

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE TYPE backup_trigger AS ENUM ('manual', 'pre_action', 'hourly')")
    op.execute("CREATE TYPE backup_status AS ENUM ('pending', 'complete', 'failed')")
    op.create_table(
        "backups",
        sa.Column("id", sa.UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tournament_id", sa.UUID, sa.ForeignKey("tournaments.id"), nullable=False),
        sa.Column(
            "triggered_by",
            sa.Enum("manual", "pre_action", "hourly", name="backup_trigger", create_type=False),
            nullable=False,
        ),
        sa.Column("pre_action_description", sa.Text, nullable=True),
        sa.Column("s3_key", sa.Text, nullable=True),
        sa.Column("size_bytes", sa.BigInteger, nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "complete", "failed", name="backup_status", create_type=False),
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
    op.execute("DROP TYPE backup_status")
    op.execute("DROP TYPE backup_trigger")
