"""Unit tests for Smart Recommendation Engine (Sprint 5).

Role: Ayushi Shukla (23ESKCS039) - AI Lead, ML Prediction, Smart Recommendations & Budget Planning
"""

import unittest
from pathlib import Path
import pandas as pd

from data_pipeline.recommendation_engine import (
    SmartRecommendationEngine,
    get_cheapest_platform,
    get_best_deals,
    generate_recommendations,
    PRODUCT_CATALOG,
    PLATFORM_CATALOG,
)

BASE_DIR = Path(__file__).resolve().parent.parent


class TestSmartRecommendationEngine(unittest.TestCase):

    def setUp(self):
        self.engine = SmartRecommendationEngine()

    def test_catalog_integrity(self):
        """Verify 6 canonical products and 4 platforms exist in catalog."""
        self.assertEqual(len(PRODUCT_CATALOG), 6)
        self.assertEqual(len(PLATFORM_CATALOG), 4)
        self.assertIn(1, PRODUCT_CATALOG)
        self.assertEqual(PRODUCT_CATALOG[1]["name"], "Amul Taaza Milk")

    def test_get_cheapest_platform_valid_product(self):
        """Verify cheapest platform identification and mathematical accuracy."""
        res = self.engine.get_cheapest_platform(1)  # Amul Taaza Milk
        self.assertTrue(res["is_available"])
        self.assertEqual(res["product_id"], 1)
        self.assertEqual(res["product_name"], "Amul Taaza Milk")
        self.assertIn("cheapest_platform", res)
        self.assertIn("cheapest_price", res)
        self.assertIn("highest_price", res)
        self.assertGreater(res["cheapest_price"], 0)
        self.assertGreaterEqual(res["highest_price"], res["cheapest_price"])
        self.assertAlmostEqual(
            res["potential_savings_inr"],
            res["highest_price"] - res["cheapest_price"],
            places=2,
        )

    def test_cheapest_platform_invalid_product_id_raises(self):
        """Invalid product IDs must raise ValueError or TypeError."""
        with self.assertRaises(ValueError):
            self.engine.get_cheapest_platform(999)

        with self.assertRaises(ValueError):
            self.engine.get_cheapest_platform(0)

        with self.assertRaises(TypeError):
            self.engine.get_cheapest_platform("invalid_id")  # type: ignore

    def test_cross_platform_savings_metrics(self):
        """Verify cross-platform savings vs highest and vs average."""
        res = self.engine.get_cross_platform_savings(2)  # Aashirvaad Atta
        self.assertTrue(res["is_available"])
        self.assertIn("average_price", res)
        self.assertIn("savings_vs_average_inr", res)
        self.assertGreaterEqual(res["average_price"], res["cheapest_price"])
        self.assertGreaterEqual(res["savings_vs_average_inr"], 0.0)

    def test_best_deal_products_ranking(self):
        """Verify deals are returned in descending order of savings percentage."""
        deals = self.engine.get_best_deal_products(top_n=5)
        self.assertGreater(len(deals), 0)
        self.assertLessEqual(len(deals), 5)

        for i in range(len(deals) - 1):
            self.assertGreaterEqual(
                deals[i]["potential_savings_pct"],
                deals[i + 1]["potential_savings_pct"],
                "Deals should be sorted descending by savings percentage",
            )

    def test_favorable_trend_products(self):
        """Verify favorable trends return structured dictionaries."""
        trends = self.engine.get_favorable_trend_products(drop_threshold_pct=0.0)
        self.assertIsInstance(trends, list)
        for t in trends:
            self.assertIn("product_name", t)
            self.assertIn("platform", t)
            self.assertIn("current_price", t)
            self.assertIn("historical_mean", t)
            self.assertGreaterEqual(t["drop_pct"], 0.0)

    def test_product_recommendation_comprehensive(self):
        """Verify end-to-end product recommendation output format."""
        rec = self.engine.get_product_recommendation(3)  # Tata Salt
        self.assertEqual(rec["product_id"], 3)
        self.assertIn(rec["decision"], ["BUY_NOW", "BUY_AS_NEEDED", "UNAVAILABLE"])
        self.assertIn("recommended_platform", rec)
        self.assertIn("summary", rec)
        self.assertIn("timing_advice", rec)

    def test_generate_all_recommendations_csv_export(self):
        """Verify dataframe generation for all 6 products."""
        recs_df = self.engine.generate_all_recommendations()
        self.assertEqual(len(recs_df), 6)
        expected_cols = [
            "product_id",
            "product_name",
            "category",
            "decision",
            "recommended_platform",
            "best_price",
            "potential_savings_inr",
            "summary",
        ]
        for col in expected_cols:
            self.assertIn(col, recs_df.columns)

    def test_functional_helpers(self):
        """Verify functional helper APIs work seamlessly."""
        cheapest = get_cheapest_platform(1)
        self.assertEqual(cheapest["product_id"], 1)

        deals = get_best_deals(top_n=3)
        self.assertLessEqual(len(deals), 3)

        df = generate_recommendations()
        self.assertEqual(len(df), 6)


if __name__ == "__main__":
    unittest.main()
