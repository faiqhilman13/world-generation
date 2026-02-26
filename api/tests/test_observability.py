def test_metrics_endpoint(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "world_generate_requests_total" in response.text


def test_viewer_open_event(client):
    response = client.post("/v1/metrics/viewer-open", json={"success": True})
    assert response.status_code == 204
