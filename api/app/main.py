from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.observability.logging import configure_logging, logging_middleware
from app.observability.tracing import configure_tracing

settings = get_settings()
configure_logging()
if settings.otel_enabled:
    configure_tracing(service_name="interior-world-api")

app = FastAPI(title=settings.app_name, debug=settings.debug)
allowed_origins = sorted(
    {
        settings.app_base_url.rstrip("/"),
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    }
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(logging_middleware)
app.include_router(api_router)
