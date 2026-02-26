import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session as OrmSession

from app.db.models import Session


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def generate_sid() -> str:
    return secrets.token_urlsafe(32)


def get_or_create_session(db: OrmSession, sid: str | None) -> Session:
    if sid:
        existing = db.query(Session).filter(Session.sid == sid).one_or_none()
        if existing is not None:
            existing.updated_at = now_utc()
            db.add(existing)
            db.commit()
            db.refresh(existing)
            return existing

    created = Session(sid=generate_sid())
    db.add(created)
    db.commit()
    db.refresh(created)
    return created


def get_session_by_sid(db: OrmSession, sid: str) -> Session | None:
    return db.query(Session).filter(Session.sid == sid).one_or_none()
