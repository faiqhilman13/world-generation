"""initial schema

Revision ID: 20260225_0001
Revises:
Create Date: 2026-02-25 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260225_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sid", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sid"),
    )
    op.create_index(op.f("ix_sessions_sid"), "sessions", ["sid"], unique=True)

    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("provider_media_asset_id", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("extension", sa.String(length=32), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("provider_payload", _json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('image', 'video', 'binary')", name="ck_media_assets_kind"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_media_asset_id"),
    )
    op.create_index(op.f("ix_media_assets_session_id"), "media_assets", ["session_id"], unique=False)

    op.create_table(
        "world_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("source_media_asset_id", sa.Uuid(), nullable=False),
        sa.Column("provider_operation_id", sa.String(length=255), nullable=True),
        sa.Column("provider_world_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress_percent", sa.Integer(), nullable=True),
        sa.Column("request_payload", _json_type(), nullable=False),
        sa.Column("operation_payload", _json_type(), nullable=False),
        sa.Column("world_payload", _json_type(), nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'succeeded', 'failed', 'expired')",
            name="ck_world_jobs_status",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_media_asset_id"], ["media_assets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_operation_id"),
        sa.UniqueConstraint("provider_world_id"),
    )
    op.create_index(op.f("ix_world_jobs_session_id"), "world_jobs", ["session_id"], unique=False)
    op.create_index(
        op.f("ix_world_jobs_source_media_asset_id"),
        "world_jobs",
        ["source_media_asset_id"],
        unique=False,
    )
    op.create_index(op.f("ix_world_jobs_status"), "world_jobs", ["status"], unique=False)

    op.create_table(
        "world_views",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("world_job_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("public", sa.Boolean(), nullable=False),
        sa.Column("world_marble_url", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["world_job_id"], ["world_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("world_job_id", name="uq_world_views_world_job_id"),
    )
    op.create_index(op.f("ix_world_views_world_job_id"), "world_views", ["world_job_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("event_payload", _json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_event_type"), "audit_logs", ["event_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_session_id"), "audit_logs", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_session_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_event_type"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_world_views_world_job_id"), table_name="world_views")
    op.drop_table("world_views")

    op.drop_index(op.f("ix_world_jobs_status"), table_name="world_jobs")
    op.drop_index(op.f("ix_world_jobs_source_media_asset_id"), table_name="world_jobs")
    op.drop_index(op.f("ix_world_jobs_session_id"), table_name="world_jobs")
    op.drop_table("world_jobs")

    op.drop_index(op.f("ix_media_assets_session_id"), table_name="media_assets")
    op.drop_table("media_assets")

    op.drop_index(op.f("ix_sessions_sid"), table_name="sessions")
    op.drop_table("sessions")
