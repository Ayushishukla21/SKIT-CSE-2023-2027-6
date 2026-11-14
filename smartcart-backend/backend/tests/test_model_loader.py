"""Model loader tests - no MySQL needed. Uses the real saved model file."""

import pytest

from app.services import model_loader, prediction_service as svc


@pytest.fixture(autouse=True)
def reset():
    svc.set_model(None)
    yield
    svc.set_model(None)


def test_loads_and_registers_model():
    assert model_loader.load_prediction_model() is True
    assert svc.get_model() is not None
    assert tuple(svc.get_model().available_periods) == (7, 30)


def test_disabled_by_env(monkeypatch):
    monkeypatch.setenv("ENABLE_PREDICTION_MODEL", "false")
    assert model_loader.load_prediction_model() is False
    assert svc.get_model() is None


def test_missing_file_is_safe(tmp_path):
    assert model_loader.load_prediction_model(tmp_path / "nope.pkl") is False
    assert svc.get_model() is None


def test_real_model_output_passes_service_validation():
    model_loader.load_prediction_model()
    history = [
        {"recorded_at": "2026-09-01T10:00:00Z", "price": 68.0},
        {"recorded_at": "2026-09-05T10:00:00Z", "price": 70.0},
    ]
    raw = svc.get_model().predict(1, 1, history, 7)
    clean = svc._clean_predictions(raw, 7)
    assert clean is not None and len(clean) == 7
    assert all(p["predicted_price"] > 0 for p in clean)
