"""Simple seed script for local development."""

from app.db.models import Session
from app.db.session import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        existing = db.query(Session).filter(Session.sid == "seed-session").one_or_none()
        if existing is None:
            db.add(Session(sid="seed-session"))
            db.commit()
            print("Seeded session: seed-session")
        else:
            print("Seed already present: seed-session")
    finally:
        db.close()


if __name__ == "__main__":
    main()
