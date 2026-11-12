"""Unit tests for price analysis, volatility, coverage, and CSV loading.

Role: Ayushi (Data Engineering, Price Analysis, ML Readiness)
"""

import unittest
from pathlib import Path
import numpy as np
import pandas as pd

from data_pipeline.coverage_audit import audit_coverage
from data_pipeline.price_analysis import analyze_historical_prices

BASE_DIR = Path(__file__).resolve().parent.parent
CLEAN_CSV = BASE_DIR / "data" / "processed" / "historical_prices_clean.csv"
RAW_CSV = BASE_DIR / "data" / "raw" / "historical_prices_raw.csv"
MAPPING_CSV = BASE_DIR / "data" / "processed" / "product_mapping.csv"
COVERAGE_CSV = BASE_DIR / "data" / "processed" / "dataset_coverage_summary.csv"
ANALYSIS_CSV = BASE_DIR / "data" / "processed" / "price_analysis_summary.csv"


class TestPriceAnalysisAndLoading(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.df = pd.read_csv(CLEAN_CSV)

    def test_all_important_csv_files_load_in_pandas(self):
        """Verify that all raw, clean, mapping, coverage, and analysis CSV files load cleanly."""
        csv_files = [
            CLEAN_CSV,
            RAW_CSV,
            MAPPING_CSV,
            COVERAGE_CSV,
            ANALYSIS_CSV,
        ]
        for path in csv_files:
            self.assertTrue(path.exists(), f"File {path.name} must exist")
            loaded = pd.read_csv(path)
            self.assertGreater(len(loaded), 0, f"File {path.name} must have rows")

    def test_coverage_audit_metrics(self):
        coverage_df, metrics = audit_coverage(self.df)
        self.assertEqual(metrics["total_combinations"], 24)
        self.assertEqual(metrics["total_products"], 6)
        self.assertEqual(metrics["total_platforms"], 4)
        self.assertEqual(metrics["expected_dates"], 40)
        self.assertEqual(metrics["insufficient_data_combinations"], 1)

    def test_tata_tea_flipkart_minutes_flagged_as_insufficient(self):
        """Tata Tea on Flipkart Minutes has 0 available observations and must be flagged."""
        coverage_df, _ = audit_coverage(self.df)
        tea_fk = coverage_df[
            (coverage_df["product_id"] == 4) & (coverage_df["platform_id"] == 4)
        ].iloc[0]
        self.assertEqual(tea_fk["available_observations"], 0)
        self.assertIn("INSUFFICIENT", tea_fk["coverage_status"])

    def test_price_analysis_volatility_calculation(self):
        """Verify volatility standard deviation and CV calculation on sufficient combinations."""
        summary_df, overview = analyze_historical_prices(self.df)
        self.assertEqual(len(summary_df), 24)

        # Check a known sufficient combination (Amul Taaza Milk on Blinkit)
        milk_blinkit = summary_df[
            (summary_df["product_id"] == 1) & (summary_df["platform_id"] == 1)
        ].iloc[0]
        self.assertEqual(milk_blinkit["data_sufficiency"], "SUFFICIENT")
        self.assertGreater(milk_blinkit["price_volatility_std"], 0.0)
        self.assertGreater(milk_blinkit["volatility_cv_pct"], 0.0)

    def test_insufficient_data_has_nan_stats(self):
        """Combinations with 0 available prices must have NaN mean and volatility."""
        summary_df, overview = analyze_historical_prices(self.df)
        tea_fk = summary_df[
            (summary_df["product_id"] == 4) & (summary_df["platform_id"] == 4)
        ].iloc[0]
        self.assertTrue(pd.isna(tea_fk["mean_price"]))
        self.assertTrue(pd.isna(tea_fk["price_volatility_std"]))
        self.assertIn("INSUFFICIENT", tea_fk["data_sufficiency"])

    def test_cheapest_platform_per_product_identified(self):
        """Cheapest platform must be identified for every product."""
        summary_df, overview = analyze_historical_prices(self.df)
        cheapest_map = overview["cheapest_platform_by_product"]
        self.assertEqual(len(cheapest_map), 6)
        for prod, plat in cheapest_map.items():
            self.assertIsNotNone(plat)
            self.assertNotEqual(plat, "")


if __name__ == "__main__":
    unittest.main()
