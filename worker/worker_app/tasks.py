from __future__ import annotations

import logging
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

from app.core.config import get_settings
from app.db.models import AuditLog, WorldJob, WorldView
from app.db.session import SessionLocal
from app.integrations.worldlabs import WorldLabsApiError, WorldLabsClient
from app.observability.metrics import (
    operation_poll_cycles_histogram,
    time_to_world_ready_seconds,
)
from worker_app.celery_app import celery_app

logger = logging.getLogger("interior_world.worker")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _provider_error_message(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None

    error_obj = payload.get("error")
    if isinstance(error_obj, dict):
        message = error_obj.get("message")
        if message:
            return str(message)

    detail = payload.get("detail")
    if isinstance(detail, str) and detail:
        return detail
    if isinstance(detail, list) and detail:
        first = detail[0]
        if isinstance(first, dict) and first.get("msg"):
            return str(first["msg"])

    message = payload.get("message")
    if message:
        return str(message)
    return None


def _call_with_retry(fn: Callable[..., dict[str, Any]], *args, **kwargs) -> dict[str, Any]:
    settings = get_settings()
    max_provider_retries = max(settings.worldlabs_provider_max_retries, 1)
    for attempt in range(max_provider_retries):
        try:
            return fn(*args, **kwargs)
        except WorldLabsApiError as exc:
            retryable = exc.status_code >= 500
            if not retryable or attempt == max_provider_retries - 1:
                raise
        except httpx.HTTPError:
            if attempt == max_provider_retries - 1:
                raise

        backoff = min(2**attempt, 10) + random.uniform(0.0, 0.25)
        time.sleep(backoff)

    raise RuntimeError("retry loop exhausted")


def _extract_world_id(operation_payload: dict[str, Any]) -> str | None:
    response = operation_payload.get("response") or {}
    metadata = operation_payload.get("metadata") or {}

    candidates = [
        response.get("world_id"),
        (response.get("world") or {}).get("world_id"),
        metadata.get("world_id"),
        (metadata.get("world") or {}).get("world_id"),
    ]
    for candidate in candidates:
        if candidate:
            return str(candidate)
    return None


def _upsert_world_view(job: WorldJob, world_payload: dict[str, Any], db_session) -> None:
    existing = db_session.query(WorldView).filter(WorldView.world_job_id == job.id).one_or_none()
    payload_permission = world_payload.get("permission") or {}

    display_name = world_payload.get("display_name") or job.request_payload.get("display_name")
    model = world_payload.get("model") or job.request_payload.get("model")
    public_value = bool(payload_permission.get("public", False))
    world_marble_url = world_payload.get("world_marble_url") or world_payload.get("viewer_url")
    thumbnail_url = world_payload.get("thumbnail_url")

    if existing is None:
        existing = WorldView(
            world_job_id=job.id,
            display_name=display_name,
            model=model,
            public=public_value,
            world_marble_url=world_marble_url,
            thumbnail_url=thumbnail_url,
        )
    else:
        existing.display_name = display_name
        existing.model = model
        existing.public = public_value
        existing.world_marble_url = world_marble_url
        existing.thumbnail_url = thumbnail_url

    db_session.add(existing)


def _mark_failure(job: WorldJob, db_session, *, code: str, message: str, status: str = "failed") -> None:
    job.status = status
    job.error_code = code
    job.error_message = message
    job.updated_at = now_utc()
    db_session.add(job)
    db_session.add(
        AuditLog(
            session_id=job.session_id,
            event_type="world_generate_failed" if status == "failed" else "world_generate_expired",
            event_payload={"job_id": str(job.id), "code": code, "message": message},
        )
    )
    db_session.commit()
    logger.error(
        "world_job_failed code=%s status=%s message=%s",
        code,
        status,
        message,
        extra={
            "event_payload": {
                "job_id": str(job.id),
                "provider_operation_id": job.provider_operation_id,
                "world_id": job.provider_world_id,
                "code": code,
                "status": status,
            }
        },
    )


@celery_app.task(name="worker.generate_world_job")
def generate_world_job(job_id: str) -> None:
    db_session = SessionLocal()
    settings = get_settings()
    client = WorldLabsClient(settings=settings)
    started_at = time.monotonic()
    poll_cycles = 0

    try:
        try:
            parsed_job_id = uuid.UUID(job_id)
        except ValueError:
            return

        job = db_session.query(WorldJob).filter(WorldJob.id == parsed_job_id).one_or_none()
        if job is None:
            return

        if job.status not in {"queued", "processing"}:
            return

        job.status = "processing"
        job.progress_percent = 5
        db_session.add(job)
        db_session.commit()
        logger.info(
            "world_job_processing",
            extra={"event_payload": {"job_id": str(job.id), "status": job.status}},
        )

        try:
            generate_payload = _call_with_retry(client.generate_world, job.request_payload)
        except WorldLabsApiError as exc:
            if exc.status_code == 402:
                code = "GENERATION_PROVIDER_402"
            elif 400 <= exc.status_code < 500:
                code = "GENERATION_PROVIDER_4XX"
            elif exc.status_code >= 500:
                code = "GENERATION_PROVIDER_5XX"
            else:
                code = "GENERATION_SUBMIT_FAILED"

            provider_message = _provider_error_message(exc.payload)
            message = provider_message or f"World Labs generate failed with status {exc.status_code}."
            _mark_failure(job, db_session, code=code, message=message)
            return

        operation_id = generate_payload.get("operation_id")
        job.provider_operation_id = operation_id
        job.operation_payload = generate_payload
        job.progress_percent = 12
        db_session.add(job)
        db_session.commit()

        final_operation_payload = generate_payload

        if not generate_payload.get("done"):
            if not operation_id:
                _mark_failure(
                    job,
                    db_session,
                    code="GENERATION_SUBMIT_FAILED",
                    message="Provider did not return operation_id for async operation.",
                )
                return

            deadline = time.monotonic() + max(settings.worldlabs_poll_horizon_seconds, 1)
            poll_interval = max(settings.worldlabs_poll_initial_seconds, 1)
            max_poll_seconds = max(settings.worldlabs_poll_max_seconds, poll_interval)
            while time.monotonic() < deadline:
                operation_payload = _call_with_retry(client.get_operation, operation_id)
                poll_cycles += 1
                final_operation_payload = operation_payload
                job.operation_payload = operation_payload
                if operation_payload.get("done"):
                    break

                current_progress = job.progress_percent or 10
                job.progress_percent = min(current_progress + 4, 95)
                db_session.add(job)
                db_session.commit()

                time.sleep(poll_interval)
                poll_interval = min(poll_interval + 1, max_poll_seconds)
            else:
                operation_poll_cycles_histogram.observe(poll_cycles)
                _mark_failure(
                    job,
                    db_session,
                    code="OPERATION_TIMEOUT",
                    message="World generation exceeded polling horizon.",
                    status="expired",
                )
                return

        if final_operation_payload.get("error"):
            provider_error = final_operation_payload.get("error") or {}
            _mark_failure(
                job,
                db_session,
                code=str(provider_error.get("code") or "GENERATION_PROVIDER_ERROR"),
                message=str(provider_error.get("message") or "Provider reported a generation failure."),
            )
            return

        world_id = _extract_world_id(final_operation_payload)
        if not world_id:
            _mark_failure(
                job,
                db_session,
                code="WORLD_FETCH_FAILED",
                message="Could not resolve world_id from operation response.",
            )
            return

        world_payload = _call_with_retry(client.get_world, world_id)
        job.provider_world_id = world_id
        job.world_payload = world_payload
        job.operation_payload = final_operation_payload
        job.status = "succeeded"
        job.progress_percent = 100
        job.error_code = None
        job.error_message = None
        job.updated_at = now_utc()
        db_session.add(job)
        _upsert_world_view(job, world_payload, db_session)
        db_session.add(
            AuditLog(
                session_id=job.session_id,
                event_type="world_generate_succeeded",
                event_payload={"job_id": str(job.id), "world_id": world_id},
            )
        )
        db_session.commit()
        operation_poll_cycles_histogram.observe(poll_cycles)
        time_to_world_ready_seconds.observe(time.monotonic() - started_at)
        logger.info(
            "world_job_succeeded",
            extra={
                "event_payload": {
                    "job_id": str(job.id),
                    "provider_operation_id": job.provider_operation_id,
                    "world_id": world_id,
                    "poll_cycles": poll_cycles,
                    "duration_seconds": round(time.monotonic() - started_at, 2),
                }
            },
        )
    except Exception as exc:  # noqa: BLE001
        if "job" in locals() and job is not None:
            operation_poll_cycles_histogram.observe(poll_cycles)
            _mark_failure(
                job,
                db_session,
                code="GENERATION_UNEXPECTED_ERROR",
                message=str(exc),
            )
    finally:
        db_session.close()
