from app.api.deps import worldlabs_client
from app.main import app


class FakeWorldLabsClient:
    def prepare_upload(self, *, file_name, kind, extension, metadata=None):
        return {
            "media_asset": {
                "media_asset_id": "media_123",
                "kind": kind,
                "file_name": file_name,
            },
            "upload_info": {
                "method": "PUT",
                "url": "https://upload.example.com/path",
                "headers": {"x-amz-acl": "private"},
            },
        }

    def get_media_asset(self, media_asset_id):
        return {"media_asset_id": media_asset_id, "status": "ready"}


def test_prepare_upload(client):
    app.dependency_overrides[worldlabs_client] = lambda: FakeWorldLabsClient()

    response = client.post(
        "/v1/uploads/prepare",
        json={
            "file_name": "room.png",
            "kind": "image",
            "extension": "png",
            "mime_type": "image/png",
            "metadata": {"source": "test"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["media_asset_id"] == "media_123"
    assert body["upload_method"] == "PUT"
    assert body["upload_url"] == "https://upload.example.com/path"
    assert body["required_headers"] == {"x-amz-acl": "private"}


def test_confirm_upload(client):
    app.dependency_overrides[worldlabs_client] = lambda: FakeWorldLabsClient()

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

    response = client.post(
        "/v1/uploads/confirm",
        json={"media_asset_id": "media_123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["confirmed"] is True
    assert body["provider_payload"]["status"] == "ready"
