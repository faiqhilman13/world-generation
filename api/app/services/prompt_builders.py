from typing import Any

from app.schemas.worlds import PromptType


def build_world_prompt(
    *,
    prompt_type: PromptType,
    source_media_asset_id: str | None,
    text_prompt: str | None,
    disable_recaption: bool | None = None,
    is_pano: bool | None = None,
    reconstruct_images: bool = False,
    reference_media_asset_ids: list[str] | None = None,
) -> dict[str, Any]:
    references = [item for item in (reference_media_asset_ids or []) if item]

    if prompt_type == "text":
        if not text_prompt:
            raise ValueError("text_prompt is required for prompt_type='text'")
        payload: dict[str, Any] = {"type": "text", "text_prompt": text_prompt}
        if disable_recaption is not None:
            payload["disable_recaption"] = disable_recaption
        return payload

    if prompt_type == "image":
        if not source_media_asset_id:
            raise ValueError("source_media_asset_id is required for prompt_type='image'")
        payload: dict[str, Any] = {
            "type": "image",
            "image_prompt": {"source": "media_asset", "media_asset_id": source_media_asset_id},
        }
        if disable_recaption is not None:
            payload["disable_recaption"] = disable_recaption
        if is_pano is not None:
            payload["is_pano"] = is_pano
        if text_prompt:
            payload["text_prompt"] = text_prompt
        return payload

    if prompt_type == "multi_image":
        media_asset_ids = [item for item in [source_media_asset_id, *references] if item]
        if not media_asset_ids:
            raise ValueError(
                "At least one media_asset_id is required for prompt_type='multi_image'"
            )
        payload = {
            "type": "multi-image",
            "multi_image_prompt": [
                {
                    "content": {
                        "source": "media_asset",
                        "media_asset_id": media_asset_id,
                    }
                }
                for media_asset_id in media_asset_ids
            ],
        }
        if disable_recaption is not None:
            payload["disable_recaption"] = disable_recaption
        if reconstruct_images:
            payload["reconstruct_images"] = True
        if text_prompt:
            payload["text_prompt"] = text_prompt
        return payload

    if prompt_type == "video":
        if not source_media_asset_id:
            raise ValueError("source_media_asset_id is required for prompt_type='video'")
        payload = {
            "type": "video",
            "video_prompt": {"source": "media_asset", "media_asset_id": source_media_asset_id},
        }
        if disable_recaption is not None:
            payload["disable_recaption"] = disable_recaption
        if text_prompt:
            payload["text_prompt"] = text_prompt
        return payload

    raise ValueError(f"Unsupported prompt_type: {prompt_type}")


def build_permission(*, public: bool) -> dict[str, Any]:
    return {
        "public": public,
        "allowed_readers": [],
        "allowed_writers": [],
    }
