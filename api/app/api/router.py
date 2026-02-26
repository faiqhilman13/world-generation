from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.observability import router as observability_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.uploads import router as uploads_router
from app.api.routes.worlds import router as worlds_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(sessions_router, prefix="/v1/sessions", tags=["sessions"])
api_router.include_router(uploads_router, prefix="/v1/uploads", tags=["uploads"])
api_router.include_router(jobs_router, prefix="/v1/jobs", tags=["jobs"])
api_router.include_router(worlds_router, prefix="/v1/worlds", tags=["worlds"])
api_router.include_router(observability_router)
