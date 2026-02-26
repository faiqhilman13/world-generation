from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.observability.metrics import record_viewer_open, render_metrics

router = APIRouter(tags=["observability"])


@router.get("/metrics")
def metrics() -> Response:
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)


class ViewerOpenEventRequest(BaseModel):
    success: bool


@router.post("/v1/metrics/viewer-open", status_code=204)
def viewer_open(event: ViewerOpenEventRequest) -> Response:
    record_viewer_open(success=event.success)
    return Response(status_code=204)
