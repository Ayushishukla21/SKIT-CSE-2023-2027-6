"""Unit tests for Smart Budget Planner (Sprint 5).

Role: Ayushi Shukla (23ESKCS039) - AI Lead, ML Prediction, Smart Recommendations & Budget Planning
"""

import unittest
from pathlib import Path
import pandas as pd

from data_pipeline.budget_planner import (
    SmartBudgetPlanner,
    plan_budget,
    PRODUCT_CATALOG,
    PLATFORM_CATALOG,
)

BASE_DIR = Path(__file__).resolve().parent.parent


class TestSmartBudgetPlanner(unittest.TestCase):

    def setUp(self):
        self.planner = SmartBudgetPlanner()
        self.valid_basket = [
            {"product_id": 1, "quantity": 2},  # Milk x 2
            {"product_id": 2, "quantity": 1},  # Atta x 1
            {"product_id": 3, "quantity": 1},  # Salt x 1
        ]

    def test_validation_empty_basket_raises(self):
        """Empty shopping basket must raise ValueError."""
        with self.assertRaises(ValueError):
            self.planner.plan_budget([], monthly_budget=500.0)

    def test_validation_invalid_budget_raises(self):
        """Negative or zero monthly budget must raise ValueError."""
        with self.assertRaises(ValueError):
            self.planner.plan_budget(self.valid_basket, monthly_budget=0.0)

        with self.assertRaises(ValueError):
            self.planner.plan_budget(self.valid_basket, monthly_budget=-100.0)

        with self.assertRaises(TypeError):
            self.planner.plan_budget(self.valid_basket, monthly_budget="five_hundred")  # type: ignore

    def test_validation_invalid_basket_items_raise(self):
        """Invalid product IDs, quantities, or duplicate items must raise ValueError."""
        # Invalid product_id
        with self.assertRaises(ValueError):
            self.planner.plan_budget([{"product_id": 99, "quantity": 1}], monthly_budget=500.0)

        # Invalid quantity <= 0
        with self.assertRaises(ValueError):
            self.planner.plan_budget([{"product_id": 1, "quantity": 0}], monthly_budget=500.0)

        with self.assertRaises(ValueError):
            self.planner.plan_budget([{"product_id": 1, "quantity": -2}], monthly_budget=500.0)

        # Duplicate product_id in same basket
        with self.assertRaises(ValueError):
            self.planner.plan_budget(
                [{"product_id": 1, "quantity": 1}, {"product_id": 1, "quantity": 2}],
                monthly_budget=500.0,
            )

    def test_single_platform_basket_evaluation(self):
        """Verify basket evaluation calculates item-level totals accurately."""
        res = self.planner.evaluate_basket_on_platform(self.valid_basket, platform_id=1)
        self.assertEqual(res["platform_id"], 1)
        self.assertEqual(res["platform_name"], "Blinkit")
        self.assertTrue(res["is_complete_basket"])
        self.assertEqual(len(res["items"]), 3)

        expected_total = sum(item["total_price"] for item in res["items"] if item["total_price"])
        self.assertAlmostEqual(res["total_cost"], round(expected_total, 2), places=2)

    def test_unavailable_item_detected_on_platform(self):
        """Tata Tea (ID 4) on Flipkart Minutes (Platform 4) is out of stock."""
        tea_basket = [{"product_id": 4, "quantity": 1}]
        res = self.planner.evaluate_basket_on_platform(tea_basket, platform_id=4)
        self.assertFalse(res["is_complete_basket"])
        self.assertEqual(len(res["missing_products"]), 1)
        self.assertEqual(res["missing_products"][0]["product_id"], 4)

    def test_budget_within_limit_status(self):
        """Verify within-budget status and remaining allowance calculation."""
        plan = self.planner.plan_budget(self.valid_basket, monthly_budget=1000.0)
        self.assertEqual(plan["status"], "SUCCESS")
        self.assertTrue(plan["is_within_budget"])
        self.assertEqual(plan["budget_status"], "WITHIN_BUDGET")
        self.assertGreater(plan["remaining_budget"], 0.0)
        self.assertEqual(plan["budget_deficit"], 0.0)
        self.assertLessEqual(plan["budget_utilization_pct"], 90.0)

    def test_over_budget_status_and_recovery_suggestions(self):
        """Verify over-budget status, deficit calculation, and recovery advice."""
        # Very low budget
        plan = self.planner.plan_budget(self.valid_basket, monthly_budget=300.0)
        self.assertEqual(plan["status"], "SUCCESS")
        self.assertFalse(plan["is_within_budget"])
        self.assertEqual(plan["budget_status"], "OVER_BUDGET")
        self.assertGreater(plan["budget_deficit"], 0.0)
        self.assertGreater(plan["budget_utilization_pct"], 100.0)

        # Check suggestions are generated
        rec_types = [r["type"] for r in plan["recommendations"]]
        self.assertIn("BUDGET_RECOVERY_QUANTITY", rec_types)

    def test_optimal_platform_identification(self):
        """Verify optimal platform has the lowest total cost among complete platforms."""
        plan = self.planner.plan_budget(self.valid_basket, monthly_budget=600.0)
        opt_cost = plan["optimal_platform_cost"]
        for p_name, p_info in plan["platform_comparison"].items():
            if p_info["is_complete"]:
                self.assertLessEqual(
                    opt_cost,
                    p_info["total_cost"],
                    f"Optimal cost {opt_cost} should be <= {p_name} cost {p_info['total_cost']}",
                )

    def test_split_cart_is_cheaper_or_equal_to_single_platform(self):
        """Split-cart optimization should never cost more than best single-platform cart."""
        plan = self.planner.plan_budget(self.valid_basket, monthly_budget=600.0)
        self.assertLessEqual(
            plan["split_cart_optimal_cost"],
            plan["optimal_platform_cost"],
            "Split cart cannot be more expensive than single platform",
        )
        self.assertGreaterEqual(plan["split_cart_extra_savings"], 0.0)

    def test_functional_helper(self):
        """Verify functional plan_budget helper works."""
        plan = plan_budget(self.valid_basket, monthly_budget=500.0)
        self.assertEqual(plan["status"], "SUCCESS")
        self.assertIn(plan["optimal_platform"], PLATFORM_CATALOG.values())


if __name__ == "__main__":
    unittest.main()
