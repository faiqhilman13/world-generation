from typing import Any

from app.schemas.worlds import PromptType


def build_world_prompt(
    *,
    prompt_type: PromptType,
    source_media_asset_id: str,
    text_prompt: str | None,
) -> dict[str, Any]:
    if prompt_type == "text":
        if not text_prompt:
            raise ValueError("text_prompt is required for prompt_type='text'")
        return {"type": "text", "text_prompt": text_prompt}

    if prompt_type == "image":
        payload: dict[str, Any] = {
            "type": "image",
            "image_prompt": {"source": "media_asset", "media_asset_id": source_media_asset_id},
        }
        if text_prompt:
            payload["text_prompt"] = text_prompt
        return payload

    if prompt_type == "multi_image":
        payload = {
            "type": "multi-image",
            "multi_image_prompt": [
                {
                    "content": {
                        "source": "media_asset",
                        "media_asset_id": source_media_asset_id,
                    }
                }
            ],
        }
        if text_prompt:
            payload["text_prompt"] = text_prompt
        return payload

    if prompt_type == "video":
        payload = {
            "type": "video",
            "video_prompt": {"source": "media_asset", "media_asset_id": source_media_asset_id},
        }
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
