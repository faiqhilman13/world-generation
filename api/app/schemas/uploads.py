from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


SUPPORTED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
SUPPORTED_VIDEO_EXTENSIONS = {"mp4", "mov", "webm"}
SUPPORTED_IMAGE_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
SUPPORTED_VIDEO_MIME_TYPES = {"video/mp4", "video/quicktime", "video/webm"}


class UploadPrepareRequest(BaseModel):
    file_name: str
    kind: Literal["image", "video"]
    extension: str = Field(min_length=1, max_length=16)
    mime_type: str = Field(min_length=1, max_length=128)
    metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_media_type(self) -> "UploadPrepareRequest":
        normalized_extension = self.extension.lower().lstrip(".")
        normalized_mime = self.mime_type.lower()

        if self.kind == "image":
            if normalized_extension not in SUPPORTED_IMAGE_EXTENSIONS:
                raise ValueError(
                    "Unsupported image extension. Allowed: jpg, jpeg, png, webp."
                )
            if normalized_mime not in SUPPORTED_IMAGE_MIME_TYPES:
                raise ValueError(
                    "Unsupported image mime_type. Allowed: image/jpeg, image/png, image/webp."
                )
        if self.kind == "video":
            if normalized_extension not in SUPPORTED_VIDEO_EXTENSIONS:
                raise ValueError(
                    "Unsupported video extension. Allowed: mp4, mov, webm."
                )
            if normalized_mime not in SUPPORTED_VIDEO_MIME_TYPES:
                raise ValueError(
                    "Unsupported video mime_type. Allowed: video/mp4, video/quicktime, video/webm."
                )

        self.extension = normalized_extension
        self.mime_type = normalized_mime
        return self


class UploadPrepareResponse(BaseModel):
    media_asset_id: str
    upload_method: str
    upload_url: str
    required_headers: dict[str, str]


class UploadConfirmRequest(BaseModel):
    media_asset_id: str


class UploadConfirmResponse(BaseModel):
    media_asset_id: str
    confirmed: bool
    provider_payload: dict[str, Any]
