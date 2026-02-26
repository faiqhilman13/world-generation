"""allow nullable source asset on world jobs

Revision ID: 20260226_0002
Revises: 20260225_0001
Create Date: 2026-02-26 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260226_0002"
down_revision: str | None = "20260225_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "world_jobs",
        "source_media_asset_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "world_jobs",
        "source_media_asset_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
