"""Unit tests for Deal and Price Drop Alert Engine (Sprint 5).

Role: Ayushi Shukla (23ESKCS039) - AI Lead, ML Prediction, Smart Recommendations & Budget Planning
"""

import unittest
from pathlib import Path
import pandas as pd

from data_pipeline.alert_engine import (
    SmartAlertEngine,
    check_price_drop_alerts,
    check_platform_deal_alerts,
    check_budget_alerts,
    PRODUCT_CATALOG,
    PLATFORM_CATALOG,
)

BASE_DIR = Path(__file__).resolve().parent.parent


class TestSmartAlertEngine(unittest.TestCase):

    def setUp(self):
        self.engine = SmartAlertEngine()

    def test_check_platform_deal_alerts(self):
        """Verify cross-platform deal alerts detection."""
        deals = self.engine.check_platform_deal_alerts(min_savings_pct=3.0)
        self.assertIsInstance(deals, list)
        self.assertGreater(len(deals), 0)

        for deal in deals:
            self.assertEqual(deal["alert_type"], "PLATFORM_DEAL")
            self.assertIn(deal["severity"], ["HIGH", "MEDIUM"])
            self.assertIn("best_platform", deal)
            self.assertIn("highest_platform", deal)
            self.assertGreaterEqual(deal["savings_pct"], 3.0)
            self.assertGreater(deal["savings_inr"], 0.0)
            self.assertIn("message", deal)

    def test_check_price_drop_alerts_structure(self):
        """Verify price drop alert output schema and mathematical consistency."""
        drops = self.engine.check_price_drop_alerts(threshold_pct=1.0, threshold_inr=0.5)
        self.assertIsInstance(drops, list)
        for drop in drops:
            self.assertEqual(drop["alert_type"], "PRICE_DROP")
            self.assertIn(drop["severity"], ["HIGH", "MEDIUM"])
            self.assertIn("old_price", drop)
            self.assertIn("new_price", drop)
            self.assertGreaterEqual(drop["old_price"], drop["new_price"])
            self.assertAlmostEqual(
                drop["drop_amount_inr"],
                drop["old_price"] - drop["new_price"],
                places=2,
            )

    def test_budget_alert_normal_returns_none(self):
        """Spending below threshold must return None (no alert needed)."""
        res = self.engine.check_budget_alerts(current_spending=2000.0, monthly_limit=5000.0)
        self.assertIsNone(res)

    def test_budget_alert_warning_threshold(self):
        """Spending between 85% and 100% must return WARNING alert."""
        res = self.engine.check_budget_alerts(current_spending=4500.0, monthly_limit=5000.0)
        self.assertIsNotNone(res)
        self.assertEqual(res["alert_type"], "BUDGET_THRESHOLD")
        self.assertEqual(res["severity"], "WARNING")
        self.assertEqual(res["utilization_pct"], 90.0)
        self.assertEqual(res["remaining_budget_inr"], 500.0)

    def test_budget_alert_critical_exceeded(self):
        """Spending over 100% must return CRITICAL alert with deficit."""
        res = self.engine.check_budget_alerts(current_spending=5500.0, monthly_limit=5000.0)
        self.assertIsNotNone(res)
        self.assertEqual(res["alert_type"], "BUDGET_THRESHOLD")
        self.assertEqual(res["severity"], "CRITICAL")
        self.assertEqual(res["utilization_pct"], 110.0)
        self.assertEqual(res["deficit_inr"], 500.0)
        self.assertIn("CRITICAL BUDGET ALERT", res["message"])

    def test_budget_alert_validation(self):
        """Invalid spending or limits must raise ValueError or TypeError."""
        with self.assertRaises(ValueError):
            self.engine.check_budget_alerts(current_spending=-50.0, monthly_limit=1000.0)

        with self.assertRaises(ValueError):
            self.engine.check_budget_alerts(current_spending=500.0, monthly_limit=0.0)

        with self.assertRaises(TypeError):
            self.engine.check_budget_alerts(current_spending="invalid", monthly_limit=1000.0)  # type: ignore

    def test_generate_active_alerts_and_csv_export(self):
        """Verify unified active alerts report generation."""
        active = self.engine.generate_active_alerts()
        self.assertIsInstance(active, list)
        self.assertGreater(len(active), 0)

        export_csv = BASE_DIR / "data" / "processed" / "active_alerts.csv"
        self.assertTrue(export_csv.exists())
        df = pd.read_csv(export_csv)
        self.assertGreater(len(df), 0)
        self.assertIn("alert_type", df.columns)
        self.assertIn("message", df.columns)

    def test_functional_helpers(self):
        """Verify helper functions return expected results."""
        deals = check_platform_deal_alerts()
        self.assertIsInstance(deals, list)

        b_warn = check_budget_alerts(current_spending=4600.0, monthly_limit=5000.0)
        self.assertIsNotNone(b_warn)
        self.assertEqual(b_warn["severity"], "WARNING")


if __name__ == "__main__":
    unittest.main()
