from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


PromptType = Literal["text", "image", "multi_image", "video"]


class WorldGenerateRequest(BaseModel):
    source_media_asset_id: str
    prompt_type: PromptType = "image"
    text_prompt: str | None = None
    display_name: str | None = None
    model: str = "Marble 0.1-mini"
    seed: int | None = None
    tags: list[str] = Field(default_factory=list)
    public: bool = False


class WorldGenerateResponse(BaseModel):
    job_id: str
    status: str


class WorldCard(BaseModel):
    world_id: str
    job_id: str
    display_name: str | None
    model: str | None
    public: bool
    world_marble_url: str | None
    thumbnail_url: str | None
    created_at: datetime


class WorldListResponse(BaseModel):
    items: list[WorldCard]
    next_cursor: str | None


class WorldDetailResponse(BaseModel):
    world_id: str
    job_id: str
    status: str
    display_name: str | None
    model: str | None
    public: bool
    world_marble_url: str | None
    thumbnail_url: str | None
    world_payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class WorldSyncRequest(BaseModel):
    page_size: int = Field(default=20, ge=1, le=100)
    page_token: str | None = None
    status: str | None = None
    model: str | None = None
    tags: list[str] | None = None
    is_public: bool | None = None
    created_after: str | None = None
    created_before: str | None = None
    sort_by: str | None = None


class WorldSyncResponse(BaseModel):
    synced_count: int
    skipped_count: int
    next_page_token: str | None
