"""
Placeholder for GET /api/products/<id>/prediction.

The ML model (Ayushi's module) is not integrated yet, so this never returns
predicted prices. It validates input, confirms the product exists, then raises
404 PREDICTION_UNAVAILABLE. When the model is ready, replace the final raise
with a response shaped like:
  {"product_id", "platform_id", "current_price", "available_periods": [7, 30],
   "predictions": [{"date", "days_ahead", "predicted_price"}]}
"""

from app.services.product_service import get_product_by_id
from app.utils.errors import invalid_parameter, prediction_unavailable


def get_prediction(product_id, platform_id=None, days_raw=None):
    if days_raw not in (None, ""):
        try:
            days = int(days_raw)
        except (TypeError, ValueError):
            raise invalid_parameter("days must be a positive integer")
        if days <= 0:
            raise invalid_parameter("days must be a positive integer")
    get_product_by_id(product_id)  # PRODUCT_NOT_FOUND / DATABASE_ERROR
    raise prediction_unavailable()
