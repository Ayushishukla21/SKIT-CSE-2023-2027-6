"""Prediction endpoint is a placeholder: always unavailable until ML integration."""


def test_prediction_unavailable(client):
    r = client.get("/api/products/1/prediction?platform_id=1&days=7")
    assert r.status_code == 404
    assert r.get_json()["error"]["code"] == "PREDICTION_UNAVAILABLE"


def test_prediction_unknown_product(client):
    r = client.get("/api/products/999999/prediction")
    assert r.status_code == 404
    assert r.get_json()["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_prediction_bad_params(client):
    assert client.get("/api/products/abc/prediction").get_json()["error"]["code"] == "INVALID_PRODUCT_ID"
    assert client.get("/api/products/1/prediction?platform_id=9").get_json()["error"]["code"] == "INVALID_PLATFORM_ID"
    assert client.get("/api/products/1/prediction?days=x").get_json()["error"]["code"] == "INVALID_PARAMETER"
