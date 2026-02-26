from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


PromptType = Literal["text", "image", "multi_image", "video"]


class WorldGenerateRequest(BaseModel):
    source_media_asset_id: str | None = None
    prompt_type: PromptType = "image"
    text_prompt: str | None = None
    disable_recaption: bool | None = None
    is_pano: bool | None = None
    reconstruct_images: bool = False
    reference_media_asset_ids: list[str] = Field(default_factory=list)
    display_name: str | None = None
    model: str = "Marble 0.1-mini"
    seed: int | None = None
    tags: list[str] = Field(default_factory=list)
    public: bool = False

    @model_validator(mode="after")
    def validate_prompt_requirements(self) -> "WorldGenerateRequest":
        normalized_source = (
            self.source_media_asset_id.strip() if self.source_media_asset_id else None
        )
        normalized_text = self.text_prompt.strip() if self.text_prompt else None

        seen: set[str] = set()
        normalized_refs: list[str] = []
        for reference_id in self.reference_media_asset_ids:
            item = reference_id.strip()
            if not item or item in seen:
                continue
            seen.add(item)
            normalized_refs.append(item)

        self.source_media_asset_id = normalized_source
        self.text_prompt = normalized_text
        self.reference_media_asset_ids = normalized_refs

        if self.prompt_type == "text":
            if not self.text_prompt:
                raise ValueError("text_prompt is required for prompt_type='text'")
            return self

        if self.prompt_type in {"image", "video"} and not self.source_media_asset_id:
            raise ValueError(
                f"source_media_asset_id is required for prompt_type='{self.prompt_type}'"
            )

        if self.prompt_type == "multi_image":
            if not self.source_media_asset_id and not self.reference_media_asset_ids:
                raise ValueError(
                    "Provide source_media_asset_id or at least one "
                    "reference_media_asset_id for prompt_type='multi_image'"
                )

        return self


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
