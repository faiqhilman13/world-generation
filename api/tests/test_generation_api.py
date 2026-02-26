from app.api.deps import job_queue_client, worldlabs_client
from app.main import app


class FakeWorldLabsClient:
    def prepare_upload(self, *, file_name, kind, extension, metadata=None):
        media_asset_id = "media_" + file_name.lower().replace(".", "_").replace("-", "_")
        return {
            "media_asset": {
                "media_asset_id": media_asset_id,
            },
            "upload_info": {
                "method": "PUT",
                "url": "https://upload.example.com/path",
                "headers": {},
            },
        }

    def get_media_asset(self, media_asset_id):
        return {"media_asset_id": media_asset_id, "status": "ready"}

    def list_worlds(self, payload):
        return {"worlds": [], "next_page_token": None}


class FakeQueueClient:
    def __init__(self):
        self.dispatched_job_ids = []

    def dispatch_generate_world_job(self, job_id: str) -> str:
        self.dispatched_job_ids.append(job_id)
        return "fake-task-id"


def test_generate_world_creates_queued_job(client):
    fake_queue = FakeQueueClient()
    app.dependency_overrides[worldlabs_client] = lambda: FakeWorldLabsClient()
    app.dependency_overrides[job_queue_client] = lambda: fake_queue

    prepare_response = client.post(
        "/v1/uploads/prepare",
        json={
            "file_name": "room.png",
            "kind": "image",
            "extension": "png",
            "mime_type": "image/png",
        },
    )
    assert prepare_response.status_code == 200
    prepared_media_asset_id = prepare_response.json()["media_asset_id"]

    generate_response = client.post(
        "/v1/worlds/generate",
        json={
            "source_media_asset_id": prepared_media_asset_id,
            "prompt_type": "image",
            "display_name": "Demo world",
            "model": "Marble 0.1-mini",
            "public": False,
            "tags": ["test"],
        },
    )
    assert generate_response.status_code == 200
    body = generate_response.json()
    assert body["status"] == "queued"
    assert body["job_id"]
    assert fake_queue.dispatched_job_ids == [body["job_id"]]

    job_response = client.get(f"/v1/jobs/{body['job_id']}")
    assert job_response.status_code == 200
    assert job_response.json()["status"] == "queued"

    world_list_response = client.get("/v1/worlds")
    assert world_list_response.status_code == 200
    assert world_list_response.json()["items"] == []

    sync_response = client.post("/v1/worlds/sync", json={"page_size": 20})
    assert sync_response.status_code == 200
    assert sync_response.json()["synced_count"] == 0


def test_generate_world_text_prompt_without_media_asset(client):
    fake_queue = FakeQueueClient()
    app.dependency_overrides[worldlabs_client] = lambda: FakeWorldLabsClient()
    app.dependency_overrides[job_queue_client] = lambda: fake_queue

    generate_response = client.post(
        "/v1/worlds/generate",
        json={
            "prompt_type": "text",
            "text_prompt": "A cozy living room with oak finishes",
            "display_name": "Text-only world",
            "model": "Marble 0.1-mini",
        },
    )
    assert generate_response.status_code == 200
    body = generate_response.json()
    assert body["status"] == "queued"
    assert fake_queue.dispatched_job_ids == [body["job_id"]]


def test_generate_world_rejects_missing_source_for_image_prompt(client):
    fake_queue = FakeQueueClient()
    app.dependency_overrides[worldlabs_client] = lambda: FakeWorldLabsClient()
    app.dependency_overrides[job_queue_client] = lambda: fake_queue

    generate_response = client.post(
        "/v1/worlds/generate",
        json={
            "prompt_type": "image",
            "display_name": "Invalid image world",
            "model": "Marble 0.1-mini",
        },
    )
    assert generate_response.status_code == 422
    assert fake_queue.dispatched_job_ids == []


def test_generate_world_multi_image_supports_reference_media_assets(client):
    fake_queue = FakeQueueClient()
    app.dependency_overrides[worldlabs_client] = lambda: FakeWorldLabsClient()
    app.dependency_overrides[job_queue_client] = lambda: fake_queue

    prepared_ids: list[str] = []
    for file_name in ("room-base.jpg", "sofa-reference.jpg", "wallpaper-reference.jpg"):
        prepare_response = client.post(
            "/v1/uploads/prepare",
            json={
                "file_name": file_name,
                "kind": "image",
                "extension": "jpg",
                "mime_type": "image/jpeg",
            },
        )
        assert prepare_response.status_code == 200
        prepared_ids.append(prepare_response.json()["media_asset_id"])

    generate_response = client.post(
        "/v1/worlds/generate",
        json={
            "source_media_asset_id": prepared_ids[0],
            "reference_media_asset_ids": prepared_ids[1:],
            "prompt_type": "multi_image",
            "text_prompt": "Use darker walnut furniture with textured beige wallpaper",
            "display_name": "Multi-image world",
            "model": "Marble 0.1-mini",
        },
    )
    assert generate_response.status_code == 200
    body = generate_response.json()
    assert body["status"] == "queued"
    assert fake_queue.dispatched_job_ids == [body["job_id"]]
