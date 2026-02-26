from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings
from app.observability.tracing import get_tracer


WORLDLABS_PREPARE_UPLOAD_PATH = "/marble/v1/media-assets:prepare_upload"
WORLDLABS_GET_MEDIA_ASSET_PATH = "/marble/v1/media-assets/{media_asset_id}"
WORLDLABS_GENERATE_WORLD_PATH = "/marble/v1/worlds:generate"
WORLDLABS_GET_WORLD_PATH = "/marble/v1/worlds/{world_id}"
WORLDLABS_LIST_WORLDS_PATH = "/marble/v1/worlds:list"
WORLDLABS_GET_OPERATION_PATH = "/marble/v1/operations/{operation_id}"


@dataclass
class WorldLabsApiError(Exception):
    status_code: int
    message: str
    payload: dict[str, Any] | None = None

    def __str__(self) -> str:
        return f"WorldLabsApiError(status={self.status_code}, message={self.message})"


class WorldLabsClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._timeout_seconds = settings.worldlabs_http_timeout_seconds
        self._tracer = get_tracer()

    def _build_url(self, path: str) -> str:
        base = self._settings.worldlabs_base_url.rstrip("/")
        if base.endswith("/marble/v1") and path.startswith("/marble/v1"):
            return f"{base}{path[len('/marble/v1'):]}"
        return f"{base}{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        allow_retry: bool = False,
    ) -> dict[str, Any]:
        headers = {
            "WLT-Api-Key": self._settings.worldlabs_api_key,
            "Accept": "application/json",
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        max_attempts = self._settings.worldlabs_provider_max_retries if allow_retry else 1
        response: httpx.Response | None = None

        for attempt in range(max(max_attempts, 1)):
            try:
                with self._tracer.start_as_current_span(f"worldlabs.{method.lower()} {path}"):
                    with httpx.Client(timeout=self._timeout_seconds) as client:
                        response = client.request(
                            method=method,
                            url=self._build_url(path),
                            headers=headers,
                            json=json_body,
                        )
            except httpx.HTTPError:
                if attempt == max_attempts - 1:
                    raise
                sleep_seconds = min(2**attempt, 10) + random.uniform(0.0, 0.2)
                time.sleep(sleep_seconds)
                continue

            if response.status_code >= 500 and attempt < max_attempts - 1:
                sleep_seconds = min(2**attempt, 10) + random.uniform(0.0, 0.2)
                time.sleep(sleep_seconds)
                continue
            break

        if response is None:
            raise RuntimeError("No response returned from World Labs request.")

        if response.status_code >= 400:
            payload: dict[str, Any] | None
            try:
                payload = response.json()
            except ValueError:
                payload = None
            raise WorldLabsApiError(
                status_code=response.status_code,
                message="World Labs request failed",
                payload=payload,
            )

        if not response.content:
            return {}
        return response.json()

    def prepare_upload(
        self,
        *,
        file_name: str,
        kind: str,
        extension: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "file_name": file_name,
            "kind": kind,
            "extension": extension,
        }
        if metadata:
            body["metadata"] = metadata
        return self._request(
            "POST",
            WORLDLABS_PREPARE_UPLOAD_PATH,
            json_body=body,
            allow_retry=True,
        )

    def get_media_asset(self, media_asset_id: str) -> dict[str, Any]:
        path = WORLDLABS_GET_MEDIA_ASSET_PATH.format(media_asset_id=media_asset_id)
        return self._request("GET", path, allow_retry=True)

    def generate_world(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", WORLDLABS_GENERATE_WORLD_PATH, json_body=payload)

    def get_world(self, world_id: str) -> dict[str, Any]:
        path = WORLDLABS_GET_WORLD_PATH.format(world_id=world_id)
        return self._request("GET", path, allow_retry=True)

    def list_worlds(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            "POST",
            WORLDLABS_LIST_WORLDS_PATH,
            json_body=payload,
            allow_retry=True,
        )

    def get_operation(self, operation_id: str) -> dict[str, Any]:
        path = WORLDLABS_GET_OPERATION_PATH.format(operation_id=operation_id)
        return self._request("GET", path, allow_retry=True)
