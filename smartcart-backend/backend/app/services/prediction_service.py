"""
GET /api/products/<id>/prediction[?platform_id=1-4&days=<n>]

No trained model is integrated yet, so by default this endpoint validates its
input, confirms the product exists, and answers 404 PREDICTION_UNAVAILABLE.
It never invents prices.

Plugging in Ayushi's model (no route change needed)
---------------------------------------------------
Implement an object with this shape and register it once at startup:

    class MyModel:
        available_periods = (7, 30)        # supported `days` horizons

        def predict(self, product_id, platform_id, history, days):
            # history: [{"recorded_at": "2026-10-01T10:00:00Z", "price": 68.0}, ...]
            #          priced observations for that platform, oldest first
            # return:  [{"date": "2026-10-23", "days_ahead": 1, "predicted_price": 67.5}, ...]
            #          one or more entries, each with 1 <= days_ahead <= days

    from app.services import prediction_service
    prediction_service.set_model(MyModel())

Everything else (validation, history lookup, safe errors, response shape) is
handled here. A model that raises, or returns malformed output, results in
404 PREDICTION_UNAVAILABLE rather than a 500 or a made-up number.

Success response:
  {"product_id", "platform_id", "current_price", "days", "available_periods",
   "predictions": [{"date", "days_ahead", "predicted_price"}]}
"""

import logging
import math
import re

from app.services import history_service
from app.services.product_service import get_product_by_id
from app.utils.errors import invalid_parameter, invalid_platform_id, prediction_unavailable

logger = logging.getLogger(__name__)

MIN_HISTORY_POINTS = 2
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_model = None


def set_model(model):
    """Register the trained model (or None to unregister)."""
    global _model
    _model = model


def get_model():
    return _model


def _number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _history(product_id, platform_id):
    return history_service.get_history(product_id, platform_id)["history"]


def _clean_predictions(raw, days):
    """Validate model output; return a clean list or None if malformed."""
    if not isinstance(raw, (list, tuple)) or not raw:
        return None
    clean = []
    for item in raw:
        if not isinstance(item, dict):
            return None
        ahead = item.get("days_ahead")
        price = item.get("predicted_price")
        date = item.get("date")
        if isinstance(ahead, bool) or not isinstance(ahead, int) or not 1 <= ahead <= days:
            return None
        if not _number(price) or price <= 0:
            return None
        if not isinstance(date, str) or not _DATE_RE.match(date):
            return None
        clean.append({"date": date, "days_ahead": ahead, "predicted_price": round(float(price), 2)})
    clean.sort(key=lambda p: p["days_ahead"])
    return clean


def get_prediction(product_id, platform_id=None, days=None):
    """
    product_id / platform_id / days are already validated by the route
    (validators.py): ints, or None for platform_id / days when omitted.
    """
    get_product_by_id(product_id)  # PRODUCT_NOT_FOUND / DATABASE_ERROR

    if platform_id is None:
        # A forecast is per platform; there is no sensible default to guess.
        raise invalid_platform_id("platform_id is required for a price prediction")

    model = get_model()
    if model is None:
        raise prediction_unavailable()

    periods = sorted(int(p) for p in model.available_periods)
    if days is None:
        days = periods[0]
    elif days not in periods:
        raise invalid_parameter(
            "days must be one of: " + ", ".join(str(p) for p in periods)
        )

    observations = _history(product_id, platform_id)
    if not observations or not observations[-1]["available"] or observations[-1]["price"] is None:
        raise prediction_unavailable(
            "Price prediction is not available: no current price for this product on this platform"
        )
    priced = [
        {"recorded_at": o["recorded_at"], "price": o["price"]}
        for o in observations
        if o["available"] and o["price"] is not None
    ]
    if len(priced) < MIN_HISTORY_POINTS:
        raise prediction_unavailable(
            "Price prediction is not available: not enough price history for this product"
        )

    try:
        raw = model.predict(product_id, platform_id, priced, days)
    except Exception:
        logger.exception("Prediction model failed")
        raise prediction_unavailable()

    predictions = _clean_predictions(raw, days)
    if predictions is None:
        logger.error("Prediction model returned malformed output")
        raise prediction_unavailable()

    return {
        "product_id": product_id,
        "platform_id": platform_id,
        "current_price": priced[-1]["price"],
        "days": days,
        "available_periods": periods,
        "predictions": predictions,
    }
