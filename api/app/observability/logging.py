import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import Request, Response

from app.observability.metrics import http_request_duration_seconds


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "event_payload"):
            payload.update(record.event_payload)
        return json.dumps(payload)


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)


async def logging_middleware(request: Request, call_next):
    logger = logging.getLogger("interior_world.api")
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()

    response: Response
    try:
        response = await call_next(request)
    except Exception:
        duration = time.perf_counter() - start
        http_request_duration_seconds.labels(
            method=request.method,
            path=request.url.path,
            status_code="500",
        ).observe(duration)
        logger.exception(
            "request_failed",
            extra={
                "event_payload": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration * 1000, 2),
                }
            },
        )
        raise

    duration = time.perf_counter() - start
    response.headers["x-request-id"] = request_id
    status_code = str(response.status_code)
    http_request_duration_seconds.labels(
        method=request.method,
        path=request.url.path,
        status_code=status_code,
    ).observe(duration)
    logger.info(
        "request_complete",
        extra={
            "event_payload": {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "session_id": request.cookies.get("sid"),
            }
        },
    )
    return response
