"""init: enable pgcrypto for gen_random_uuid()

Revision ID: 0001
Revises:
Create Date: 2026-04-29

"""

from collections.abc import Sequence

from alembic import op  # type: ignore[attr-defined]

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')


def downgrade() -> None:
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
