from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session as OrmSession

from app.api.deps import db_session
from app.core.config import get_settings
from app.schemas.session import SessionBootstrapResponse
from app.services.session_service import get_or_create_session

router = APIRouter()


@router.post("/bootstrap", response_model=SessionBootstrapResponse)
def bootstrap_session(
    request: Request,
    response: Response,
    db: OrmSession = Depends(db_session),
) -> SessionBootstrapResponse:
    settings = get_settings()
    sid = request.cookies.get(settings.session_cookie_name)
    session = get_or_create_session(db=db, sid=sid)

    response.set_cookie(
        key=settings.session_cookie_name,
        value=session.sid,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.session_cookie_max_age_seconds,
    )

    return SessionBootstrapResponse.model_validate(session)
