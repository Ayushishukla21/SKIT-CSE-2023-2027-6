"""
Loads the trained price model (models/price_prediction_model.pkl, built by
data_pipeline/price_prediction_model.py) and registers it with
prediction_service. Called once from run.py - NOT from create_app(), so the
test-suite keeps its "no model" behaviour.

Safe by design: if the model cannot be loaded for any reason, we log it and
leave prediction_service without a model (endpoint answers 404
PREDICTION_UNAVAILABLE). Set ENABLE_PREDICTION_MODEL=false to skip loading.
"""

import logging
import os
import sys
from pathlib import Path

from app.services import prediction_service

logger = logging.getLogger(__name__)

# .../repo/smartcart-backend/backend/app/services/model_loader.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[4]


def load_prediction_model(model_path=None):
    """Return True if a model was registered, False otherwise."""
    if os.getenv("ENABLE_PREDICTION_MODEL", "true").lower() != "true":
        logger.info("Prediction model disabled by ENABLE_PREDICTION_MODEL")
        return False
    try:
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from data_pipeline.price_prediction_model import SmartCartPricePredictor

        predictor = SmartCartPricePredictor.load(Path(model_path) if model_path else None)
    except Exception:
        logger.exception("Could not load prediction model; endpoint stays unavailable")
        return False
    prediction_service.set_model(predictor)
    logger.info("Prediction model registered (demo-trained)")
    return True
