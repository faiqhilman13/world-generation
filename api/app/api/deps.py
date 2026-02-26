from collections.abc import Generator

from sqlalchemy.orm import Session as OrmSession

from app.core.config import get_settings
from app.db.session import get_db
from app.integrations.job_queue import JobQueueClient
from app.integrations.worldlabs import WorldLabsClient


def db_session() -> Generator[OrmSession, None, None]:
    yield from get_db()


def worldlabs_client() -> WorldLabsClient:
    return WorldLabsClient(settings=get_settings())


def job_queue_client() -> JobQueueClient:
    return JobQueueClient()
