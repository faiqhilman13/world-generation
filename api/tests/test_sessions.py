def test_bootstrap_creates_session_and_sets_cookie(client):
    response = client.post("/v1/sessions/bootstrap")

    assert response.status_code == 200
    body = response.json()
    assert body["sid"]
    assert "sid=" in response.headers["set-cookie"]


def test_bootstrap_reuses_sid_cookie(client):
    first = client.post("/v1/sessions/bootstrap")
    sid = first.json()["sid"]

    second = client.post(
        "/v1/sessions/bootstrap",
        cookies={"sid": sid},
    )

    assert second.status_code == 200
    assert second.json()["sid"] == sid
