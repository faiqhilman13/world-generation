from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


JobStatus = Literal["queued", "processing", "succeeded", "failed", "expired"]


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress_percent: int | None
    provider_operation_id: str | None
    world_id: str | None
    error: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
