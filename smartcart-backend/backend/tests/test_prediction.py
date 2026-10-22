"""
Tests for GET /api/products/<id>/prediction.

Part 1 (DB-backed) needs the seeded local MySQL like the other endpoint tests.
Part 2 (mocked) replaces the product lookup and history query, so it needs no
MySQL, and uses a fake model - it only checks the service interface. No real
ML model exists yet and none of these tests claims one does.
"""

import pytest

from app.services import prediction_service as svc
from app.utils.errors import ApiError, product_not_found

OK_HISTORY = [
    {"platform_id": 1, "price": 68.0, "currency": "INR", "available": True, "recorded_at": "2026-10-01T10:00:00Z"},
    {"platform_id": 1, "price": 70.0, "currency": "INR", "available": True, "recorded_at": "2026-10-08T10:00:00Z"},
]


@pytest.fixture(autouse=True)
def no_model_after_test():
    svc.set_model(None)
    yield
    svc.set_model(None)


# ---------------- Part 1: real DB (seeded demo data) ----------------

def test_prediction_unavailable(client):
    r = client.get("/api/products/1/prediction?platform_id=1&days=7")
    assert r.status_code == 404
    assert r.get_json()["error"]["code"] == "PREDICTION_UNAVAILABLE"


def test_prediction_unknown_product(client):
    r = client.get("/api/products/999999/prediction?platform_id=1")
    assert r.status_code == 404
    assert r.get_json()["error"]["code"] == "PRODUCT_NOT_FOUND"


# ---------------- Part 2: no MySQL needed ----------------

class FakeModel:
    available_periods = (7, 30)

    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.calls = []

    def predict(self, product_id, platform_id, history, days):
        self.calls.append((product_id, platform_id, history, days))
        if self.exc:
            raise self.exc
        if self.result is not None:
            return self.result
        return [{"date": "2026-10-29", "days_ahead": days, "predicted_price": 71.456}]


@pytest.fixture()
def mocked(monkeypatch):
    state = {"history": list(OK_HISTORY), "exists": True}

    def fake_product(pid):
        if not state["exists"] or pid == 999999:
            raise product_not_found()
        return {"id": pid}

    monkeypatch.setattr(svc, "get_product_by_id", fake_product)
    monkeypatch.setattr(svc, "_history", lambda pid, plat: state["history"])
    return state


def code(r):
    return r.get_json()["error"]["code"]


@pytest.mark.parametrize("url,expected", [
    ("/api/products/abc/prediction?platform_id=1", "INVALID_PRODUCT_ID"),
    ("/api/products/0/prediction?platform_id=1", "INVALID_PRODUCT_ID"),
    ("/api/products/-3/prediction?platform_id=1", "INVALID_PRODUCT_ID"),
    ("/api/products/1/prediction?platform_id=0", "INVALID_PLATFORM_ID"),
    ("/api/products/1/prediction?platform_id=5", "INVALID_PLATFORM_ID"),
    ("/api/products/1/prediction?platform_id=abc", "INVALID_PLATFORM_ID"),
    ("/api/products/1/prediction?platform_id=1&days=0", "INVALID_PARAMETER"),
    ("/api/products/1/prediction?platform_id=1&days=-7", "INVALID_PARAMETER"),
    ("/api/products/1/prediction?platform_id=1&days=7.5", "INVALID_PARAMETER"),
    ("/api/products/1/prediction?platform_id=1&days=abc", "INVALID_PARAMETER"),
    ("/api/products/1/prediction?platform_id=1&days=366", "INVALID_PARAMETER"),
])
def test_invalid_inputs_use_error_format(client, mocked, url, expected):
    r = client.get(url)
    assert r.status_code == 400
    assert r.get_json() == {"error": {"code": expected, "message": r.get_json()["error"]["message"]}}
    assert isinstance(r.get_json()["error"]["message"], str)


def test_platform_id_required(client, mocked):
    r = client.get("/api/products/1/prediction")
    assert r.status_code == 400
    assert code(r) == "INVALID_PLATFORM_ID"


def test_unknown_product(client, mocked):
    r = client.get("/api/products/999999/prediction?platform_id=1&days=7")
    assert r.status_code == 404
    assert code(r) == "PRODUCT_NOT_FOUND"


def test_unknown_product_even_with_model(client, mocked):
    svc.set_model(FakeModel())
    assert code(client.get("/api/products/999999/prediction?platform_id=1")) == "PRODUCT_NOT_FOUND"


def test_model_unavailable(client, mocked):
    r = client.get("/api/products/1/prediction?platform_id=1&days=7")
    assert r.status_code == 404
    assert code(r) == "PREDICTION_UNAVAILABLE"
    assert "predictions" not in r.get_json()


def test_missing_history(client, mocked):
    svc.set_model(FakeModel())
    mocked["history"] = []
    r = client.get("/api/products/1/prediction?platform_id=1&days=7")
    assert r.status_code == 404
    assert code(r) == "PREDICTION_UNAVAILABLE"


def test_insufficient_history(client, mocked):
    svc.set_model(FakeModel())
    mocked["history"] = OK_HISTORY[:1]
    assert code(client.get("/api/products/1/prediction?platform_id=1&days=7")) == "PREDICTION_UNAVAILABLE"


def test_currently_unavailable_platform(client, mocked):
    svc.set_model(FakeModel())
    mocked["history"] = OK_HISTORY + [
        {"platform_id": 1, "price": None, "currency": "INR", "available": False, "recorded_at": "2026-10-15T10:00:00Z"}
    ]
    assert code(client.get("/api/products/1/prediction?platform_id=1&days=7")) == "PREDICTION_UNAVAILABLE"


def test_success_response_format(client, mocked):
    model = FakeModel()
    svc.set_model(model)
    r = client.get("/api/products/1/prediction?platform_id=1&days=7")
    assert r.status_code == 200
    assert r.get_json() == {
        "product_id": 1,
        "platform_id": 1,
        "current_price": 70.0,
        "days": 7,
        "available_periods": [7, 30],
        "predictions": [{"date": "2026-10-29", "days_ahead": 7, "predicted_price": 71.46}],
    }
    assert model.calls == [(1, 1, [
        {"recorded_at": "2026-10-01T10:00:00Z", "price": 68.0},
        {"recorded_at": "2026-10-08T10:00:00Z", "price": 70.0},
    ], 7)]


def test_days_defaults_to_first_period(client, mocked):
    svc.set_model(FakeModel())
    assert client.get("/api/products/1/prediction?platform_id=1").get_json()["days"] == 7


def test_days_not_supported_by_model(client, mocked):
    svc.set_model(FakeModel())
    r = client.get("/api/products/1/prediction?platform_id=1&days=10")
    assert r.status_code == 400
    assert code(r) == "INVALID_PARAMETER"


@pytest.mark.parametrize("bad", [
    None, [], "x", [1], [{}],
    [{"date": "2026-10-29", "days_ahead": 7, "predicted_price": None}],
    [{"date": "2026-10-29", "days_ahead": 7, "predicted_price": -1}],
    [{"date": "2026-10-29", "days_ahead": 7, "predicted_price": float("nan")}],
    [{"date": "2026-10-29", "days_ahead": 7, "predicted_price": True}],
    [{"date": "29/10/2026", "days_ahead": 7, "predicted_price": 70}],
    [{"date": "2026-10-29", "days_ahead": 99, "predicted_price": 70}],
])
def test_malformed_model_output_is_unavailable(client, mocked, bad):
    svc.set_model(FakeModel(result=bad if bad is not None else "x"))
    r = client.get("/api/products/1/prediction?platform_id=1&days=7")
    assert r.status_code == 404
    assert code(r) == "PREDICTION_UNAVAILABLE"


def test_model_exception_is_unavailable_not_500(client, mocked):
    svc.set_model(FakeModel(exc=RuntimeError("secret internal detail")))
    r = client.get("/api/products/1/prediction?platform_id=1&days=7")
    assert r.status_code == 404
    assert code(r) == "PREDICTION_UNAVAILABLE"
    assert "secret" not in r.get_data(as_text=True)


def test_api_error_type_is_used(mocked):
    with pytest.raises(ApiError):
        svc.get_prediction(1, 1, 7)
