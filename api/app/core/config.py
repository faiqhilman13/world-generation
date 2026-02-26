from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Interior World API"
    app_env: str = "dev"
    debug: bool = False

    worldlabs_api_key: str = Field(default="replace-me", alias="WORLDLABS_API_KEY")
    worldlabs_base_url: str = Field(
        default="https://api.worldlabs.ai", alias="WORLDLABS_BASE_URL"
    )

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/interior_world",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    session_cookie_secret: str = Field(
        default="replace-me", alias="SESSION_COOKIE_SECRET"
    )
    app_base_url: str = Field(default="http://localhost:3000", alias="APP_BASE_URL")
    worldlabs_http_timeout_seconds: int = Field(
        default=30, alias="WORLDLABS_HTTP_TIMEOUT_SECONDS"
    )
    worldlabs_provider_max_retries: int = Field(
        default=8, alias="WORLDLABS_PROVIDER_MAX_RETRIES"
    )
    worldlabs_poll_initial_seconds: int = Field(
        default=2, alias="WORLDLABS_POLL_INITIAL_SECONDS"
    )
    worldlabs_poll_max_seconds: int = Field(
        default=10, alias="WORLDLABS_POLL_MAX_SECONDS"
    )
    worldlabs_poll_horizon_seconds: int = Field(
        default=1200, alias="WORLDLABS_POLL_HORIZON_SECONDS"
    )
    otel_enabled: bool = Field(default=True, alias="OTEL_ENABLED")

    session_cookie_name: str = "sid"
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"
    session_cookie_max_age_seconds: int = 60 * 60 * 24 * 30

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
