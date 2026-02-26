from app.api.deps import job_queue_client, worldlabs_client
from app.main import app


class FakeWorldLabsClient:
    def prepare_upload(self, *, file_name, kind, extension, metadata=None):
        return {
            "media_asset": {
                "media_asset_id": "media_for_generation",
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

    generate_response = client.post(
        "/v1/worlds/generate",
        json={
            "source_media_asset_id": "media_for_generation",
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
