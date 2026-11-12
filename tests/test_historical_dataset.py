"""Tests for SmartCart AI historical price dataset and validation pipeline.

Role: Ayushi (Data Engineering, Dataset Validation, ML Readiness)
"""

import unittest
from pathlib import Path
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split

from validate_dataset import validate_historical_dataset, VALID_PRODUCT_IDS, VALID_PLATFORM_IDS

BASE_DIR = Path(__file__).resolve().parent.parent
CLEAN_CSV_PATH = BASE_DIR / "data" / "processed" / "historical_prices_clean.csv"
RAW_CSV_PATH = BASE_DIR / "data" / "raw" / "historical_prices_raw.csv"
MAPPING_CSV_PATH = BASE_DIR / "data" / "processed" / "product_mapping.csv"


class TestHistoricalDataset(unittest.TestCase):

    def setUp(self):
        self.assertTrue(CLEAN_CSV_PATH.exists(), "Clean historical dataset must exist")
        self.df = pd.read_csv(CLEAN_CSV_PATH)

    def test_file_exists_and_loads(self):
        self.assertGreater(len(self.df), 500)
        self.assertEqual(len(self.df), 960)

    def test_validator_passes(self):
        passed, summary, issues = validate_historical_dataset(CLEAN_CSV_PATH)
        self.assertTrue(passed, f"Validation failed with issues: {issues}")
        self.assertEqual(summary["Duplicate rows"], 0)
        self.assertEqual(summary["Invalid prices"], 0)
        self.assertEqual(summary["Products"], 6)
        self.assertEqual(summary["Platforms"], 4)

    def test_required_columns_exist(self):
        expected_cols = [
            "product_id",
            "product_name",
            "brand",
            "category",
            "platform_id",
            "platform",
            "price",
            "currency",
            "available",
            "recorded_at",
            "quantity",
            "unit",
            "discount_amount",
            "effective_price",
        ]
        for col in expected_cols:
            self.assertIn(col, self.df.columns)

    def test_identifiers_have_no_nulls(self):
        mandatory_fields = [
            "product_id",
            "product_name",
            "brand",
            "category",
            "platform_id",
            "platform",
            "currency",
            "available",
            "recorded_at",
            "quantity",
            "unit",
        ]
        for field in mandatory_fields:
            self.assertEqual(
                self.df[field].isna().sum(),
                0,
                f"Column {field} should not have nulls",
            )

    def test_product_and_platform_ids_valid(self):
        unique_pids = set(self.df["product_id"].unique())
        self.assertEqual(unique_pids, VALID_PRODUCT_IDS)

        unique_plat_ids = set(self.df["platform_id"].unique())
        self.assertEqual(unique_plat_ids, VALID_PLATFORM_IDS)

    def test_unavailable_products_have_null_price_not_zero(self):
        unavail = self.df[self.df["available"] == False]
        self.assertGreater(len(unavail), 0, "There should be test unavailable rows")
        
        # Price must be NaN / null, NOT 0
        self.assertTrue(
            unavail["price"].isna().all(),
            "Unavailable products must have NaN price, NOT 0",
        )
        self.assertTrue(
            unavail["effective_price"].isna().all(),
            "Unavailable products must have NaN effective_price",
        )

    def test_available_products_have_positive_price(self):
        avail = self.df[self.df["available"] == True]
        self.assertTrue(
            avail["price"].notna().all(),
            "Available products must have numeric price",
        )
        self.assertTrue(
            (avail["price"] > 0).all(),
            "Available products must have price > 0",
        )

    def test_sorting_order(self):
        sorted_tuples = list(zip(self.df["product_id"], self.df["platform_id"], self.df["recorded_at"]))
        self.assertEqual(
            sorted_tuples,
            sorted(sorted_tuples),
            "Dataset must be sorted by (product_id, platform_id, recorded_at)",
        )

    def test_no_duplicate_observations(self):
        dups = self.df.duplicated(subset=["product_id", "platform_id", "recorded_at"]).sum()
        self.assertEqual(dups, 0, "There should be 0 duplicate observations")

    def test_product_mapping_exists_and_valid(self):
        self.assertTrue(MAPPING_CSV_PATH.exists(), "Product mapping CSV must exist")
        mapping_df = pd.read_csv(MAPPING_CSV_PATH)
        self.assertGreater(len(mapping_df), 15)
        self.assertIn("canonical_product_id", mapping_df.columns)
        self.assertIn("raw_title", mapping_df.columns)

    def test_ml_readiness_baseline_feature_engineering_and_model_fit(self):
        """Verify the dataset supports time-series ML price prediction (Sprint 4 preparation)."""
        df = self.df[self.df["available"] == True].copy()
        
        # Feature engineering: date features
        df["recorded_dt"] = pd.to_datetime(df["recorded_at"])
        df["day_of_week"] = df["recorded_dt"].dt.dayofweek
        df["day_of_month"] = df["recorded_dt"].dt.day
        
        # Lag features within product/platform series
        df["lag_1_price"] = df.groupby(["product_id", "platform_id"])["price"].shift(1)
        
        # Drop initial NaN from shift
        ml_data = df.dropna(subset=["lag_1_price"]).copy()
        self.assertGreater(len(ml_data), 500)

        # One-hot encode categoricals
        X = pd.get_dummies(
            ml_data[["product_id", "platform_id", "day_of_week", "day_of_month", "lag_1_price"]],
            columns=["product_id", "platform_id"],
            drop_first=True,
        )
        y = ml_data["price"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        model = Ridge()
        model.fit(X_train, y_train)
        score = model.score(X_test, y_test)
        
        # High R^2 expected because lag price is strongly predictive of current price
        self.assertGreater(score, 0.85, f"Baseline ML model R^2 score should be high, got: {score}")


if __name__ == "__main__":
    unittest.main()
