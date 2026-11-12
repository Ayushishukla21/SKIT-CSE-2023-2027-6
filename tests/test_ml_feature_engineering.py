"""Unit tests for ML feature engineering and data leakage prevention.

Role: Ayushi (Data Engineering, ML Feature Engineering, ML Readiness)
"""

import unittest
from pathlib import Path
import numpy as np
import pandas as pd

from data_pipeline.feature_engineering import generate_ml_features

BASE_DIR = Path(__file__).resolve().parent.parent
CLEAN_CSV = BASE_DIR / "data" / "processed" / "historical_prices_clean.csv"
ML_CSV = BASE_DIR / "data" / "processed" / "ml_ready_prices.csv"


class TestMLFeatureEngineering(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.clean_df = pd.read_csv(CLEAN_CSV)
        cls.ml_df = generate_ml_features(cls.clean_df)

    def test_ml_ready_file_exists_and_loads(self):
        self.assertTrue(ML_CSV.exists())
        df = pd.read_csv(ML_CSV)
        self.assertEqual(len(df), len(self.clean_df))
        self.assertEqual(len(df), 960)

    def test_required_ml_columns_present(self):
        expected_cols = [
            "product_id",
            "platform_id",
            "price",
            "available",
            "recorded_at",
            "day_of_week",
            "month",
            "prev_recorded_at",
            "prev_price",
            "price_change",
            "price_change_pct",
        ]
        for col in expected_cols:
            self.assertIn(col, self.ml_df.columns)

    def test_first_observation_has_nan_previous_price(self):
        """First observation of each product-platform series must have NaN previous price."""
        grouped = self.ml_df.groupby(["product_id", "platform_id"])
        for _, group in grouped:
            first_row = group.iloc[0]
            self.assertTrue(
                pd.isna(first_row["prev_price"]),
                "First row in each combination series must have NaN prev_price",
            )
            self.assertTrue(
                pd.isna(first_row["price_change"]),
                "First row in each combination series must have NaN price_change",
            )

    def test_previous_price_matches_preceding_valid_price(self):
        """Row t must receive price from row t-1 within the same product/platform."""
        sample_group = self.ml_df[
            (self.ml_df["product_id"] == 1) & (self.ml_df["platform_id"] == 1)
        ].reset_index(drop=True)

        for i in range(1, len(sample_group)):
            expected_prev = sample_group.loc[i - 1, "price"]
            actual_prev = sample_group.loc[i, "prev_price"]
            self.assertEqual(actual_prev, expected_prev)

            expected_diff = round(sample_group.loc[i, "price"] - expected_prev, 2)
            actual_diff = sample_group.loc[i, "price_change"]
            self.assertAlmostEqual(actual_diff, expected_diff, places=2)

    def test_no_cross_platform_leakage(self):
        """Features must reset when transitioning between platforms."""
        p1_plat1_last = self.ml_df[
            (self.ml_df["product_id"] == 1) & (self.ml_df["platform_id"] == 1)
        ].iloc[-1]["price"]

        p1_plat2_first = self.ml_df[
            (self.ml_df["product_id"] == 1) & (self.ml_df["platform_id"] == 2)
        ].iloc[0]

        self.assertTrue(
            pd.isna(p1_plat2_first["prev_price"]),
            "Previous price must NOT leak across platforms",
        )
        self.assertNotEqual(p1_plat2_first["prev_price"], p1_plat1_last)

    def test_no_future_data_leakage(self):
        """Changing future prices must NOT alter past features."""
        df_copy = self.clean_df.copy()
        features_orig = generate_ml_features(df_copy)

        # Alter the last 5 days of data
        df_altered = self.clean_df.copy()
        df_altered.loc[df_altered.index[-5:], "price"] = 999.99
        features_altered = generate_ml_features(df_altered)

        # First 50 rows must remain 100% identical
        orig_head = features_orig.iloc[:50][["prev_price", "price_change"]]
        altered_head = features_altered.iloc[:50][["prev_price", "price_change"]]
        pd.testing.assert_frame_equal(orig_head, altered_head)

    def test_unavailable_products_do_not_use_zero(self):
        """Out of stock items must have NaN price and changes, NEVER ₹0."""
        unavail = self.ml_df[self.ml_df["available"] == False]
        self.assertGreater(len(unavail), 0)
        self.assertTrue(unavail["price"].isna().all(), "Price must be NaN when unavailable")
        self.assertTrue(
            unavail["price_change"].isna().all(),
            "Price change must be NaN when current price is unavailable",
        )
        self.assertTrue((unavail["price"] != 0).all())

    def test_calendar_features(self):
        """Day of week should be in 0..6 and month in 1..12."""
        self.assertTrue(self.ml_df["day_of_week"].isin(list(range(7))).all())
        self.assertTrue(self.ml_df["month"].isin(list(range(1, 13))).all())

    def test_clean_dataset_is_preserved(self):
        """Original clean CSV must remain identical after feature engineering."""
        clean_after = pd.read_csv(CLEAN_CSV)
        self.assertEqual(len(clean_after), 960)
        self.assertEqual(clean_after.shape[1], 14)


if __name__ == "__main__":
    unittest.main()
