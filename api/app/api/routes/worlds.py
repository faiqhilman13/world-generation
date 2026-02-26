from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session as OrmSession

from app.api.deps import db_session, job_queue_client, worldlabs_client
from app.core.config import get_settings
from app.db.models import AuditLog, MediaAsset, WorldJob, WorldView
from app.integrations.job_queue import JobQueueClient
from app.integrations.worldlabs import WorldLabsApiError, WorldLabsClient
from app.observability.metrics import world_generate_failures_total, world_generate_requests_total
from app.schemas.worlds import (
    WorldCard,
    WorldDetailResponse,
    WorldGenerateRequest,
    WorldGenerateResponse,
    WorldListResponse,
    WorldSyncRequest,
    WorldSyncResponse,
)
from app.services.prompt_builders import build_permission, build_world_prompt
from app.services.session_service import get_or_create_session

router = APIRouter()

@router.post("/generate", response_model=WorldGenerateResponse)
def generate_world(
    payload: WorldGenerateRequest,
    request: Request,
    response: Response,
    db: OrmSession = Depends(db_session),
    queue: JobQueueClient = Depends(job_queue_client),
) -> WorldGenerateResponse:
    world_generate_requests_total.inc()
    settings = get_settings()
    sid = request.cookies.get(settings.session_cookie_name)
    session = get_or_create_session(db=db, sid=sid)
    if sid != session.sid:
        response.set_cookie(
            key=settings.session_cookie_name,
            value=session.sid,
            httponly=True,
            secure=settings.session_cookie_secure,
            samesite=settings.session_cookie_samesite,
            max_age=settings.session_cookie_max_age_seconds,
        )

    source_asset = None
    if payload.source_media_asset_id:
        source_asset = (
            db.query(MediaAsset)
            .filter(
                MediaAsset.provider_media_asset_id == payload.source_media_asset_id,
                MediaAsset.session_id == session.id,
            )
            .one_or_none()
        )
        if source_asset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="source_media_asset_id not found for this session",
            )

    reference_ids: list[str] = []
    seen_reference_ids: set[str] = set()
    for media_asset_id in payload.reference_media_asset_ids:
        if (
            not media_asset_id
            or media_asset_id == payload.source_media_asset_id
            or media_asset_id in seen_reference_ids
        ):
            continue
        seen_reference_ids.add(media_asset_id)
        reference_ids.append(media_asset_id)
    if reference_ids:
        reference_assets = (
            db.query(MediaAsset)
            .filter(
                MediaAsset.provider_media_asset_id.in_(reference_ids),
                MediaAsset.session_id == session.id,
            )
            .all()
        )
        existing_reference_ids = {
            reference_asset.provider_media_asset_id for reference_asset in reference_assets
        }
        missing_references = [
            media_asset_id
            for media_asset_id in reference_ids
            if media_asset_id not in existing_reference_ids
        ]
        if missing_references:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "reference_media_asset_ids not found for this session: "
                    + ", ".join(missing_references)
                ),
            )

    try:
        world_prompt = build_world_prompt(
            prompt_type=payload.prompt_type,
            source_media_asset_id=payload.source_media_asset_id,
            text_prompt=payload.text_prompt,
            disable_recaption=payload.disable_recaption,
            is_pano=payload.is_pano,
            reconstruct_images=payload.reconstruct_images,
            reference_media_asset_ids=reference_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    provider_request_payload = {
        "world_prompt": world_prompt,
        "display_name": payload.display_name,
        "model": payload.model,
        "permission": build_permission(public=payload.public),
        "seed": payload.seed,
        "tags": payload.tags,
    }

    job = WorldJob(
        session_id=session.id,
        source_media_asset_id=source_asset.id if source_asset else None,
        status="queued",
        progress_percent=0,
        request_payload=provider_request_payload,
    )
    db.add(job)
    db.flush()
    db.add(
        AuditLog(
            session_id=session.id,
            event_type="world_generate_queued",
            event_payload={"job_id": str(job.id)},
        )
    )
    db.commit()
    db.refresh(job)

    try:
        queue.dispatch_generate_world_job(str(job.id))
    except Exception as exc:  # noqa: BLE001
        world_generate_failures_total.inc()
        job.status = "failed"
        job.error_code = "QUEUE_DISPATCH_FAILED"
        job.error_message = str(exc)
        db.add(job)
        db.commit()
        db.refresh(job)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to dispatch generation job",
        ) from exc

    return WorldGenerateResponse(job_id=str(job.id), status=job.status)


@router.get("", response_model=WorldListResponse)
def list_worlds(
    request: Request,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=50),
    db: OrmSession = Depends(db_session),
) -> WorldListResponse:
    settings = get_settings()
    sid = request.cookies.get(settings.session_cookie_name)
    session = get_or_create_session(db=db, sid=sid)

    offset = 0
    if cursor:
        try:
            offset = max(int(cursor), 0)
        except ValueError:
            offset = 0

    rows = (
        db.query(WorldView, WorldJob)
        .join(WorldJob, WorldView.world_job_id == WorldJob.id)
        .filter(WorldJob.session_id == session.id)
        .order_by(WorldView.created_at.desc())
        .offset(offset)
        .limit(limit + 1)
        .all()
    )

    has_next = len(rows) > limit
    page_rows = rows[:limit]

    cards = [
        WorldCard(
            world_id=job.provider_world_id or "",
            job_id=str(job.id),
            display_name=view.display_name,
            model=view.model,
            public=view.public,
            world_marble_url=view.world_marble_url,
            thumbnail_url=view.thumbnail_url,
            created_at=view.created_at,
        )
        for view, job in page_rows
        if job.provider_world_id
    ]

    next_cursor = str(offset + limit) if has_next else None
    return WorldListResponse(items=cards, next_cursor=next_cursor)


@router.get("/{world_id}", response_model=WorldDetailResponse)
def get_world_detail(
    world_id: str,
    request: Request,
    db: OrmSession = Depends(db_session),
) -> WorldDetailResponse:
    settings = get_settings()
    sid = request.cookies.get(settings.session_cookie_name)
    session = get_or_create_session(db=db, sid=sid)

    job = (
        db.query(WorldJob)
        .filter(
            WorldJob.provider_world_id == world_id,
            WorldJob.session_id == session.id,
        )
        .one_or_none()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="World not found")

    view = db.query(WorldView).filter(WorldView.world_job_id == job.id).one_or_none()
    return WorldDetailResponse(
        world_id=world_id,
        job_id=str(job.id),
        status=job.status,
        display_name=view.display_name if view else None,
        model=view.model if view else None,
        public=view.public if view else False,
        world_marble_url=view.world_marble_url if view else None,
        thumbnail_url=view.thumbnail_url if view else None,
        world_payload=job.world_payload,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post("/sync", response_model=WorldSyncResponse)
def sync_worlds_from_provider(
    payload: WorldSyncRequest,
    request: Request,
    db: OrmSession = Depends(db_session),
    client: WorldLabsClient = Depends(worldlabs_client),
) -> WorldSyncResponse:
    settings = get_settings()
    sid = request.cookies.get(settings.session_cookie_name)
    session = get_or_create_session(db=db, sid=sid)

    try:
        provider_payload = client.list_worlds(
            payload.model_dump(exclude_none=True),
        )
    except WorldLabsApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "WORLD_SYNC_FAILED",
                "provider_status": exc.status_code,
                "provider_payload": exc.payload or {},
            },
        ) from exc

    worlds = provider_payload.get("worlds") or provider_payload.get("items") or []
    synced_count = 0
    skipped_count = 0

    for provider_world in worlds:
        provider_world_id = provider_world.get("world_id")
        if not provider_world_id:
            skipped_count += 1
            continue

        job = (
            db.query(WorldJob)
            .filter(
                WorldJob.provider_world_id == provider_world_id,
                WorldJob.session_id == session.id,
            )
            .one_or_none()
        )
        if job is None:
            skipped_count += 1
            continue

        job.world_payload = provider_world
        db.add(job)

        view = db.query(WorldView).filter(WorldView.world_job_id == job.id).one_or_none()
        permission = provider_world.get("permission") or {}
        if view is None:
            view = WorldView(
                world_job_id=job.id,
                display_name=provider_world.get("display_name"),
                model=provider_world.get("model"),
                public=bool(permission.get("public", False)),
                world_marble_url=provider_world.get("world_marble_url"),
                thumbnail_url=provider_world.get("thumbnail_url"),
            )
        else:
            view.display_name = provider_world.get("display_name")
            view.model = provider_world.get("model")
            view.public = bool(permission.get("public", False))
            view.world_marble_url = provider_world.get("world_marble_url")
            view.thumbnail_url = provider_world.get("thumbnail_url")
        db.add(view)
        synced_count += 1

    db.commit()
    next_token = provider_payload.get("next_page_token") or provider_payload.get("nextPageToken")
    return WorldSyncResponse(
        synced_count=synced_count,
        skipped_count=skipped_count,
        next_page_token=next_token,
    )
