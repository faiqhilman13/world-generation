from celery import Celery

from app.core.config import get_settings


class JobQueueClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = Celery(
            "interior_world_api_dispatcher",
            broker=settings.redis_url,
            backend=settings.redis_url,
        )

    def dispatch_generate_world_job(self, job_id: str) -> str:
        result = self._client.send_task("worker.generate_world_job", args=[job_id])
        return result.id
