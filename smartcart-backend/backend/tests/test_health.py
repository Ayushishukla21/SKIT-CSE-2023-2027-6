def test_health_shape(client):
    """
    /api/health always returns this exact shape, whether the database is
    connected (200) or not (503) - it never uses the standard error envelope.
    To manually test the 503 case, stop MySQL and hit this endpoint again.
    """
    response = client.get("/api/health")
    assert response.status_code in (200, 503)

    data = response.get_json()
    assert data["service"] == "smartcart-api"
    assert data["contract_version"] == "1.0"
    assert data["status"] in ("ok", "error")
    assert data["database"] in ("connected", "disconnected")

    if response.status_code == 200:
        assert data["status"] == "ok"
        assert data["database"] == "connected"
    else:
        assert data["status"] == "error"
        assert data["database"] == "disconnected"
