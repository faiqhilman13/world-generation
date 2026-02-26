import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from sqlalchemy.orm import Session as OrmSession

from app.api.deps import db_session, worldlabs_client
from app.core.config import get_settings
from app.db.models import AuditLog, MediaAsset
from app.integrations.worldlabs import WorldLabsApiError, WorldLabsClient
from app.schemas.uploads import (
    UploadConfirmRequest,
    UploadConfirmResponse,
    UploadPrepareRequest,
    UploadPrepareResponse,
)
from app.services.session_service import get_or_create_session

router = APIRouter()


def _extract_upload_fields(payload: dict) -> tuple[str, str, dict[str, str]]:
    upload_info = payload.get("upload_info") or {}
    method = (
        upload_info.get("method")
        or upload_info.get("upload_method")
        or upload_info.get("http_method")
        or "PUT"
    )
    upload_url = upload_info.get("url") or upload_info.get("upload_url")
    if not upload_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Provider response missing upload URL",
        )
    headers = upload_info.get("headers") or upload_info.get("required_headers") or {}
    return method, upload_url, headers


@router.post("/prepare", response_model=UploadPrepareResponse)
def prepare_upload(
    payload: UploadPrepareRequest,
    request: Request,
    response: Response,
    db: OrmSession = Depends(db_session),
    client: WorldLabsClient = Depends(worldlabs_client),
) -> UploadPrepareResponse:
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

    try:
        provider_payload = client.prepare_upload(
            file_name=payload.file_name,
            kind=payload.kind,
            extension=payload.extension,
            metadata=payload.metadata,
        )
    except WorldLabsApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "UPLOAD_PREPARE_FAILED",
                "provider_status": exc.status_code,
                "provider_payload": exc.payload or {},
            },
        ) from exc

    media_asset = provider_payload.get("media_asset") or {}
    media_asset_id = media_asset.get("media_asset_id")
    if not media_asset_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Provider response missing media_asset.media_asset_id",
        )

    method, upload_url, required_headers = _extract_upload_fields(provider_payload)

    existing = (
        db.query(MediaAsset)
        .filter(MediaAsset.provider_media_asset_id == media_asset_id)
        .one_or_none()
    )
    if existing is None:
        record = MediaAsset(
            session_id=session.id,
            provider_media_asset_id=media_asset_id,
            file_name=payload.file_name,
            kind=payload.kind,
            extension=payload.extension,
            mime_type=payload.mime_type,
            provider_payload=provider_payload,
        )
        db.add(record)
    else:
        existing.provider_payload = provider_payload
        existing.file_name = payload.file_name
        existing.kind = payload.kind
        existing.extension = payload.extension
        existing.mime_type = payload.mime_type
        db.add(existing)

    db.add(
        AuditLog(
            session_id=session.id,
            event_type="upload_prepared",
            event_payload={"provider_media_asset_id": media_asset_id},
        )
    )
    db.commit()

    return UploadPrepareResponse(
        media_asset_id=media_asset_id,
        upload_method=method,
        upload_url=upload_url,
        required_headers=required_headers,
    )


@router.post("/confirm", response_model=UploadConfirmResponse)
def confirm_upload(
    payload: UploadConfirmRequest,
    request: Request,
    response: Response,
    db: OrmSession = Depends(db_session),
    client: WorldLabsClient = Depends(worldlabs_client),
) -> UploadConfirmResponse:
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

    asset = (
        db.query(MediaAsset)
        .filter(
            MediaAsset.provider_media_asset_id == payload.media_asset_id,
            MediaAsset.session_id == session.id,
        )
        .one_or_none()
    )
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media asset not found for this session",
        )

    try:
        provider_payload = client.get_media_asset(payload.media_asset_id)
    except WorldLabsApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "UPLOAD_CONFIRM_FAILED",
                "provider_status": exc.status_code,
                "provider_payload": exc.payload or {},
            },
        ) from exc

    asset.provider_payload = provider_payload
    db.add(asset)
    db.add(
        AuditLog(
            session_id=session.id,
            event_type="upload_confirmed",
            event_payload={"provider_media_asset_id": payload.media_asset_id},
        )
    )
    db.commit()

    return UploadConfirmResponse(
        media_asset_id=payload.media_asset_id,
        confirmed=True,
        provider_payload=provider_payload,
    )


@router.post("/proxy")
async def proxy_upload(
    request: Request,
    response: Response,
    media_asset_id: str = Form(...),
    file: UploadFile = File(...),
    db: OrmSession = Depends(db_session),
) -> dict[str, object]:
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

    asset = (
        db.query(MediaAsset)
        .filter(
            MediaAsset.provider_media_asset_id == media_asset_id,
            MediaAsset.session_id == session.id,
        )
        .one_or_none()
    )
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media asset not found for this session",
        )

    method, upload_url, required_headers = _extract_upload_fields(asset.provider_payload)
    upload_method = method.upper()
    if upload_method not in {"PUT", "POST"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported upload method for proxy: {upload_method}",
        )

    content = await file.read()
    with httpx.Client(timeout=60) as client:
        upstream_response = client.request(
            method=upload_method,
            url=upload_url,
            headers=required_headers,
            content=content,
        )

    if upstream_response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "UPLOAD_PROXY_FAILED",
                "provider_status": upstream_response.status_code,
                "provider_body": upstream_response.text[:500],
            },
        )

    db.add(
        AuditLog(
            session_id=session.id,
            event_type="upload_proxy_completed",
            event_payload={"provider_media_asset_id": media_asset_id},
        )
    )
    db.commit()

    return {"media_asset_id": media_asset_id, "uploaded": True}
