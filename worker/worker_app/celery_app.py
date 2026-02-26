import os

from celery import Celery

from worker_app.logging import configure_worker_logging

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
configure_worker_logging()

celery_app = Celery(
    "interior_world_worker",
    broker=redis_url,
    backend=redis_url,
    include=["worker_app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
