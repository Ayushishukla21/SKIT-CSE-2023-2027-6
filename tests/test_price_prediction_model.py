"""Automated tests for Price Prediction Machine Learning Model.

Role: Ayushi Shukla (23ESKCS039) - AI Lead, ML Prediction
Sprint: Sprint 4 - ML Price Prediction
"""

import json
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

from data_pipeline.price_prediction_model import (
    FEATURE_COLS,
    MODEL_PATH,
    METADATA_PATH,
    TARGET_COL,
    SmartCartPricePredictor,
    build_preprocessor,
    load_and_prepare_dataset,
    split_chronologically,
    train_and_compare_models,
    train_and_save_pipeline,
)


class TestPricePredictionModel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.predictor, cls.metadata = train_and_save_pipeline()

    def test_feature_preparation_excludes_target_variable(self):
        """Verify target_price is strictly not included in input features (no data leakage)."""
        df = load_and_prepare_dataset()
        self.assertIn(TARGET_COL, df.columns)
        self.assertNotIn(TARGET_COL, FEATURE_COLS)
        self.assertNotIn("price", FEATURE_COLS)

        X = df[FEATURE_COLS]
        self.assertNotIn(TARGET_COL, X.columns)
        self.assertNotIn("price", X.columns)

    def test_missing_values_handled_appropriately(self):
        """Verify no zero or negative target prices in prepared dataset."""
        df = load_and_prepare_dataset()
        self.assertTrue((df[TARGET_COL] > 0).all())
        self.assertFalse(df[TARGET_COL].isna().any())

    def test_chronological_split_prevents_lookahead_leakage(self):
        """Verify all training timestamps are strictly prior or equal to test timestamps."""
        df = load_and_prepare_dataset()
        train_df, test_df = split_chronologically(df, test_ratio=0.33)

        self.assertGreater(len(train_df), 0)
        self.assertGreater(len(test_df), 0)
        self.assertLessEqual(
            train_df["recorded_at_dt"].max(),
            test_df["recorded_at_dt"].min(),
            "Training dates must not overlap or exceed test dates",
        )

    def test_model_training_and_evaluation_metrics(self):
        """Verify candidate algorithms (Linear Regression, Decision Tree, Random Forest) are evaluated."""
        df = load_and_prepare_dataset()
        train_df, test_df = split_chronologically(df, test_ratio=0.33)
        metrics, best_name, _ = train_and_compare_models(train_df, test_df)

        expected_algorithms = ["Linear Regression", "Decision Tree", "Random Forest"]
        for alg in expected_algorithms:
            self.assertIn(alg, metrics)
            scores = metrics[alg]
            self.assertGreater(scores["mae"], 0.0)
            self.assertGreater(scores["mse"], 0.0)
            self.assertGreater(scores["rmse"], 0.0)
            self.assertLessEqual(scores["r2_score"], 1.0)
            self.assertGreater(scores["r2_score"], 0.8)

        self.assertIn(best_name, expected_algorithms)

    def test_model_serialization_and_loading(self):
        """Verify model pipeline and metadata are successfully serialized and reloadable."""
        self.assertTrue(MODEL_PATH.exists(), f"Model file must exist at {MODEL_PATH}")
        self.assertTrue(METADATA_PATH.exists(), f"Metadata file must exist at {METADATA_PATH}")

        loaded_predictor = SmartCartPricePredictor.load(MODEL_PATH)
        self.assertIsNotNone(loaded_predictor.model)
        self.assertEqual(loaded_predictor.available_periods, (7, 30))

        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            meta = json.load(f)
        self.assertIn("models_evaluated", meta)
        self.assertIn("best_model", meta)
        self.assertIn("available_periods", meta)

    def test_7_day_prediction_format_and_properties(self):
        """Verify 7-day prediction produces valid, structured forecasts."""
        history = [
            {"recorded_at": "2026-09-01T10:00:00Z", "price": 68.0},
            {"recorded_at": "2026-09-05T10:00:00Z", "price": 70.0},
        ]
        preds = self.predictor.predict(product_id=1, platform_id=1, history=history, days=7)

        self.assertEqual(len(preds), 7)
        for i, p in enumerate(preds, start=1):
            self.assertEqual(p["days_ahead"], i)
            self.assertIn("date", p)
            self.assertIn("predicted_price", p)
            self.assertGreater(p["predicted_price"], 0.0)
            # Date must be YYYY-MM-DD
            parts = p["date"].split("-")
            self.assertEqual(len(parts), 3)

    def test_30_day_prediction_format_and_properties(self):
        """Verify 30-day prediction produces 30 consecutive daily forecasts."""
        history = [
            {"recorded_at": "2026-09-01T10:00:00Z", "price": 265.0},
            {"recorded_at": "2026-09-05T10:00:00Z", "price": 270.0},
        ]
        preds = self.predictor.predict(product_id=2, platform_id=1, history=history, days=30)

        self.assertEqual(len(preds), 30)
        self.assertEqual(preds[0]["days_ahead"], 1)
        self.assertEqual(preds[-1]["days_ahead"], 30)
        for p in preds:
            self.assertGreater(p["predicted_price"], 0.0)

    def test_invalid_parameters_raise_value_errors(self):
        """Verify invalid product IDs, platform IDs, days or insufficient history raise ValueError."""
        history = [{"recorded_at": "2026-09-01T10:00:00Z", "price": 68.0}]

        # Insufficient history (< 2 points)
        with self.assertRaises(ValueError):
            self.predictor.predict(product_id=1, platform_id=1, history=history, days=7)

        valid_history = [
            {"recorded_at": "2026-09-01T10:00:00Z", "price": 68.0},
            {"recorded_at": "2026-09-05T10:00:00Z", "price": 70.0},
        ]

        # Invalid days
        with self.assertRaises(ValueError):
            self.predictor.predict(product_id=1, platform_id=1, history=valid_history, days=15)

        # Invalid product_id
        with self.assertRaises(ValueError):
            self.predictor.predict(product_id=999, platform_id=1, history=valid_history, days=7)

        # Invalid platform_id
        with self.assertRaises(ValueError):
            self.predictor.predict(product_id=1, platform_id=999, history=valid_history, days=7)

    def test_compatibility_with_backend_prediction_service(self):
        """Verify model matches the exact interface expected by smartcart-backend's prediction_service."""
        import sys
        backend_dir = Path(__file__).resolve().parent.parent / "smartcart-backend" / "backend"
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))

        from app.services import prediction_service as svc

        # Model registers cleanly
        svc.set_model(self.predictor)
        self.assertIs(svc.get_model(), self.predictor)

        # Output conforms to _clean_predictions logic
        history = [
            {"recorded_at": "2026-09-01T10:00:00Z", "price": 68.0},
            {"recorded_at": "2026-09-05T10:00:00Z", "price": 70.0},
        ]
        raw_preds = self.predictor.predict(1, 1, history, 7)
        cleaned = svc._clean_predictions(raw_preds, days=7)
        self.assertIsNotNone(cleaned)
        self.assertEqual(len(cleaned), 7)

        # Cleanup
        svc.set_model(None)


if __name__ == "__main__":
    unittest.main()
