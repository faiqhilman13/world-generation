import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.db.session import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def json_type():
    return JSON().with_variant(JSONB, "postgresql")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        onupdate=now_utc,
        server_default=func.now(),
    )

    media_assets: Mapped[list["MediaAsset"]] = relationship(back_populates="session")
    world_jobs: Mapped[list["WorldJob"]] = relationship(back_populates="session")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="session")


class MediaAsset(Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint("kind IN ('image', 'video', 'binary')", name="ck_media_assets_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_media_asset_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    file_name: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="image")
    extension: Mapped[str | None] = mapped_column(String(32))
    mime_type: Mapped[str | None] = mapped_column(String(128))
    provider_payload: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        onupdate=now_utc,
        server_default=func.now(),
    )

    session: Mapped[Session] = relationship(back_populates="media_assets")
    world_jobs: Mapped[list["WorldJob"]] = relationship(back_populates="source_media_asset")


class WorldJob(Base):
    __tablename__ = "world_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'processing', 'succeeded', 'failed', 'expired')",
            name="ck_world_jobs_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_media_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=True, index=True
    )
    provider_operation_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    provider_world_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    progress_percent: Mapped[int | None] = mapped_column(Integer)
    request_payload: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)
    operation_payload: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)
    world_payload: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        onupdate=now_utc,
        server_default=func.now(),
    )

    session: Mapped[Session] = relationship(back_populates="world_jobs")
    source_media_asset: Mapped[MediaAsset | None] = relationship(back_populates="world_jobs")
    world_view: Mapped["WorldView | None"] = relationship(
        back_populates="world_job", uselist=False
    )


class WorldView(Base):
    __tablename__ = "world_views"
    __table_args__ = (UniqueConstraint("world_job_id", name="uq_world_views_world_job_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    world_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("world_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    display_name: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(128))
    public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    world_marble_url: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        onupdate=now_utc,
        server_default=func.now(),
    )

    world_job: Mapped[WorldJob] = relationship(back_populates="world_view")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_payload: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc, server_default=func.now()
    )

    session: Mapped[Session] = relationship(back_populates="audit_logs")
