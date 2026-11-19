"""Deal and Price Drop Alert Engine for SmartCart AI.

Role: Ayushi Shukla (23ESKCS039) - AI Lead, ML Prediction, Smart Recommendations & Budget Planning
Sprint 5: Deal Discovery and Price Drop Alert Logic

Capabilities:
1. Detect price drop alerts across quick-commerce platforms.
2. Detect cross-platform deal alerts when one platform offers substantial discounts.
3. Monitor grocery budget consumption and trigger warning/critical budget alerts.
4. Provide decoupled alert condition evaluation ready for notification services.
5. Export active alerts to data/processed/active_alerts.csv.
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

HISTORICAL_CLEAN_CSV = PROCESSED_DIR / "historical_prices_clean.csv"
PROCESSED_PRICES_CSV = PROCESSED_DIR / "processed_prices.csv"
PRICE_CHANGES_CSV = PROCESSED_DIR / "price_changes.csv"
ACTIVE_ALERTS_CSV = PROCESSED_DIR / "active_alerts.csv"

PRODUCT_CATALOG: Dict[int, Dict[str, Any]] = {
    1: {"name": "Amul Taaza Milk", "brand": "Amul", "category": "Dairy"},
    2: {"name": "Aashirvaad Atta", "brand": "Aashirvaad", "category": "Staples"},
    3: {"name": "Tata Salt", "brand": "Tata", "category": "Staples"},
    4: {"name": "Tata Tea", "brand": "Tata", "category": "Beverages"},
    5: {"name": "Maggi 2-Minute Noodles", "brand": "Nestle", "category": "Packaged Food"},
    6: {"name": "Parle-G Biscuits", "brand": "Parle", "category": "Snacks"},
}

PLATFORM_CATALOG: Dict[int, str] = {
    1: "Blinkit",
    2: "Zepto",
    3: "Instamart",
    4: "Flipkart Minutes",
}


class SmartAlertEngine:
    """Detection and generation engine for grocery price drops, platform deals, and budget alerts."""

    ALERT_TYPE_PRICE_DROP = "PRICE_DROP"
    ALERT_TYPE_PLATFORM_DEAL = "PLATFORM_DEAL"
    ALERT_TYPE_BUDGET_THRESHOLD = "BUDGET_THRESHOLD"

    def __init__(
        self,
        snapshot_df: Optional[pd.DataFrame] = None,
        historical_df: Optional[pd.DataFrame] = None,
        price_changes_df: Optional[pd.DataFrame] = None,
    ) -> None:
        """Initialize engine with datasets or load from disk."""
        if snapshot_df is not None:
            self.snapshot_df = snapshot_df.copy()
        elif PROCESSED_PRICES_CSV.exists():
            self.snapshot_df = pd.read_csv(PROCESSED_PRICES_CSV)
        else:
            self.snapshot_df = pd.DataFrame()

        if historical_df is not None:
            self.historical_df = historical_df.copy()
        elif HISTORICAL_CLEAN_CSV.exists():
            self.historical_df = pd.read_csv(HISTORICAL_CLEAN_CSV)
        else:
            self.historical_df = pd.DataFrame()

        if price_changes_df is not None:
            self.price_changes_df = price_changes_df.copy()
        elif PRICE_CHANGES_CSV.exists():
            self.price_changes_df = pd.read_csv(PRICE_CHANGES_CSV)
        else:
            self.price_changes_df = pd.DataFrame()

    def check_price_drop_alerts(
        self,
        threshold_pct: float = 2.0,
        threshold_inr: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """Identify recent significant price drops across products and platforms."""
        alerts: List[Dict[str, Any]] = []

        if not self.price_changes_df.empty:
            df = self.price_changes_df.copy()
            # Look for price drops where price_change < 0
            if "price_change" in df.columns and "price_change_pct" in df.columns:
                drops = df[
                    (df["price_change"] <= -threshold_inr)
                    | (df["price_change_pct"] <= -threshold_pct)
                ].copy()

                for _, row in drops.iterrows():
                    p_id = int(row["product_id"])
                    plat_id = int(row["platform_id"])
                    p_name = row.get("product_name", PRODUCT_CATALOG.get(p_id, {}).get("name", f"Product {p_id}"))
                    plat_name = row.get("platform", PLATFORM_CATALOG.get(plat_id, f"Platform {plat_id}"))
                    old_p = float(row.get("prev_price", row.get("price", 0) - row["price_change"]))
                    new_p = float(row["price"])
                    drop_amt = round(abs(float(row["price_change"])), 2)
                    drop_pct = round(abs(float(row["price_change_pct"])), 2)

                    severity = "HIGH" if drop_pct >= 5.0 or drop_amt >= 5.0 else "MEDIUM"
                    alerts.append({
                        "alert_type": self.ALERT_TYPE_PRICE_DROP,
                        "product_id": p_id,
                        "product_name": p_name,
                        "platform_id": plat_id,
                        "platform": plat_name,
                        "old_price": round(old_p, 2),
                        "new_price": round(new_p, 2),
                        "drop_amount_inr": drop_amt,
                        "drop_pct": drop_pct,
                        "severity": severity,
                        "recorded_at": str(row.get("recorded_at", "")),
                        "message": (
                            f"Price Drop Alert: {p_name} dropped by INR {drop_amt:.2f} "
                            f"({drop_pct:.1f}%) on {plat_name}! Now INR {new_p:.2f} (was INR {old_p:.2f})."
                        ),
                    })

        elif not self.historical_df.empty:
            # Fall back to computing lag difference from historical_df
            hist = self.historical_df.copy().sort_values("recorded_at")
            avail = hist[hist["available"].astype(str).str.lower().isin(["true", "1", "yes"])].copy()
            avail["prev_price"] = avail.groupby(["product_id", "platform_id"])["price"].shift(1)
            avail["price_change"] = avail["price"] - avail["prev_price"]
            avail["price_change_pct"] = (avail["price_change"] / avail["prev_price"]) * 100

            drops = avail[
                (avail["price_change"] <= -threshold_inr)
                | (avail["price_change_pct"] <= -threshold_pct)
            ].copy()

            for _, row in drops.iterrows():
                p_id = int(row["product_id"])
                plat_id = int(row["platform_id"])
                p_name = row.get("product_name", PRODUCT_CATALOG.get(p_id, {}).get("name", f"Product {p_id}"))
                plat_name = row.get("platform", PLATFORM_CATALOG.get(plat_id, f"Platform {plat_id}"))
                old_p = float(row["prev_price"])
                new_p = float(row["price"])
                drop_amt = round(abs(float(row["price_change"])), 2)
                drop_pct = round(abs(float(row["price_change_pct"])), 2)

                severity = "HIGH" if drop_pct >= 5.0 or drop_amt >= 5.0 else "MEDIUM"
                alerts.append({
                    "alert_type": self.ALERT_TYPE_PRICE_DROP,
                    "product_id": p_id,
                    "product_name": p_name,
                    "platform_id": plat_id,
                    "platform": plat_name,
                    "old_price": round(old_p, 2),
                    "new_price": round(new_p, 2),
                    "drop_amount_inr": drop_amt,
                    "drop_pct": drop_pct,
                    "severity": severity,
                    "recorded_at": str(row.get("recorded_at", "")),
                    "message": (
                        f"Price Drop Alert: {p_name} dropped by INR {drop_amt:.2f} "
                        f"({drop_pct:.1f}%) on {plat_name}! Now INR {new_p:.2f} (was INR {old_p:.2f})."
                    ),
                })

        return alerts

    def check_platform_deal_alerts(
        self, min_savings_pct: float = 4.0
    ) -> List[Dict[str, Any]]:
        """Identify products where one platform offers a significant deal compared to competitors."""
        alerts: List[Dict[str, Any]] = []
        if self.snapshot_df.empty:
            return alerts

        snap = self.snapshot_df.copy()
        is_avail = snap["available"].astype(str).str.lower().isin(["true", "1", "yes"])
        valid_snap = snap[is_avail & snap["price"].notna() & (snap["price"] > 0)].copy()

        for p_id in PRODUCT_CATALOG:
            p_obs = valid_snap[valid_snap["product_id"] == p_id].copy()
            if len(p_obs) < 2:
                continue

            p_obs = p_obs.sort_values("price")
            cheapest = p_obs.iloc[0]
            most_expensive = p_obs.iloc[-1]

            min_price = float(cheapest["price"])
            max_price = float(most_expensive["price"])
            savings_inr = round(max_price - min_price, 2)
            savings_pct = round((savings_inr / max_price) * 100, 2) if max_price > 0 else 0.0

            if savings_pct >= min_savings_pct:
                cheapest_plat_id = int(cheapest["platform_id"])
                cheapest_plat_name = PLATFORM_CATALOG.get(cheapest_plat_id, f"Platform {cheapest_plat_id}")
                highest_plat_id = int(most_expensive["platform_id"])
                highest_plat_name = PLATFORM_CATALOG.get(highest_plat_id, f"Platform {highest_plat_id}")
                prod_name = PRODUCT_CATALOG[p_id]["name"]

                severity = "HIGH" if savings_pct >= 7.0 else "MEDIUM"
                alerts.append({
                    "alert_type": self.ALERT_TYPE_PLATFORM_DEAL,
                    "product_id": p_id,
                    "product_name": prod_name,
                    "best_platform_id": cheapest_plat_id,
                    "best_platform": cheapest_plat_name,
                    "best_price": round(min_price, 2),
                    "highest_platform_id": highest_plat_id,
                    "highest_platform": highest_plat_name,
                    "highest_price": round(max_price, 2),
                    "savings_inr": savings_inr,
                    "savings_pct": savings_pct,
                    "severity": severity,
                    "message": (
                        f"Platform Deal Alert: {prod_name} is cheapest on {cheapest_plat_name} "
                        f"at INR {min_price:.2f} (Save INR {savings_inr:.2f} / {savings_pct:.1f}% vs {highest_plat_name})."
                    ),
                })

        alerts.sort(key=lambda x: x["savings_pct"], reverse=True)
        return alerts

    def check_budget_alerts(
        self,
        current_spending: float,
        monthly_limit: float,
        warning_threshold_pct: float = 85.0,
    ) -> Optional[Dict[str, Any]]:
        """Evaluate spending against monthly budget limit and generate alerts."""
        if not isinstance(current_spending, (int, float, np.number)):
            raise TypeError("current_spending must be numeric")
        if not isinstance(monthly_limit, (int, float, np.number)):
            raise TypeError("monthly_limit must be numeric")

        if current_spending < 0:
            raise ValueError(f"current_spending cannot be negative, got {current_spending}")
        if monthly_limit <= 0:
            raise ValueError(f"monthly_limit must be a positive number > 0, got {monthly_limit}")

        utilization_pct = round((current_spending / monthly_limit) * 100, 2)
        remaining = round(monthly_limit - current_spending, 2)

        if utilization_pct > 100.0:
            deficit = round(current_spending - monthly_limit, 2)
            return {
                "alert_type": self.ALERT_TYPE_BUDGET_THRESHOLD,
                "severity": "CRITICAL",
                "current_spending": round(current_spending, 2),
                "monthly_limit": round(monthly_limit, 2),
                "utilization_pct": utilization_pct,
                "deficit_inr": deficit,
                "message": (
                    f"CRITICAL BUDGET ALERT: You have exceeded your monthly budget of INR {monthly_limit:.2f} "
                    f"by INR {deficit:.2f} (Total spending: INR {current_spending:.2f}, {utilization_pct}% utilized)."
                ),
            }
        elif utilization_pct >= warning_threshold_pct:
            return {
                "alert_type": self.ALERT_TYPE_BUDGET_THRESHOLD,
                "severity": "WARNING",
                "current_spending": round(current_spending, 2),
                "monthly_limit": round(monthly_limit, 2),
                "utilization_pct": utilization_pct,
                "remaining_budget_inr": remaining,
                "message": (
                    f"BUDGET WARNING: You have utilized {utilization_pct}% of your monthly budget. "
                    f"INR {remaining:.2f} remaining out of INR {monthly_limit:.2f}."
                ),
            }

        return None

    def generate_active_alerts(
        self, output_path: Optional[Path] = None
    ) -> List[Dict[str, Any]]:
        """Compile all active price drops and platform deals into a unified report and save to CSV."""
        all_alerts: List[Dict[str, Any]] = []

        # 1. Platform deal alerts
        deal_alerts = self.check_platform_deal_alerts(min_savings_pct=4.0)
        all_alerts.extend(deal_alerts)

        # 2. Price drop alerts
        price_drop_alerts = self.check_price_drop_alerts(threshold_pct=2.0, threshold_inr=1.0)
        # Avoid duplicate alert records
        all_alerts.extend(price_drop_alerts)

        if all_alerts:
            export_rows = []
            for a in all_alerts:
                export_rows.append({
                    "alert_type": a["alert_type"],
                    "product_id": a.get("product_id"),
                    "product_name": a.get("product_name"),
                    "platform": a.get("platform", a.get("best_platform")),
                    "severity": a.get("severity"),
                    "savings_inr": a.get("savings_inr", a.get("drop_amount_inr")),
                    "savings_pct": a.get("savings_pct", a.get("drop_pct")),
                    "message": a.get("message"),
                })
            df = pd.DataFrame(export_rows)
            save_path = output_path or ACTIVE_ALERTS_CSV
            save_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(save_path, index=False)
            logger.info(f"Saved {len(df)} active alerts to {save_path}")

        return all_alerts


# Functional Helper APIs
def check_price_drop_alerts(threshold_pct: float = 2.0) -> List[Dict[str, Any]]:
    """Helper function to scan for price drop alerts."""
    engine = SmartAlertEngine()
    return engine.check_price_drop_alerts(threshold_pct=threshold_pct)


def check_platform_deal_alerts(min_savings_pct: float = 4.0) -> List[Dict[str, Any]]:
    """Helper function to scan for platform deal alerts."""
    engine = SmartAlertEngine()
    return engine.check_platform_deal_alerts(min_savings_pct=min_savings_pct)


def check_budget_alerts(
    current_spending: float,
    monthly_limit: float,
    warning_threshold_pct: float = 85.0,
) -> Optional[Dict[str, Any]]:
    """Helper function to check budget alerts."""
    engine = SmartAlertEngine()
    return engine.check_budget_alerts(
        current_spending=current_spending,
        monthly_limit=monthly_limit,
        warning_threshold_pct=warning_threshold_pct,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 65)
    print("SmartCart AI: Deal and Price Drop Alert Engine (Sprint 5 - Ayushi)")
    print("=" * 65)

    engine = SmartAlertEngine()
    active_alerts = engine.generate_active_alerts()
    print(f"\nGenerated {len(active_alerts)} active alerts:")
    for a in active_alerts[:6]:
        print(f" * [{a['alert_type']}] [{a['severity']}] {a['message']}")

    # Demo budget alerts
    print("\nBudget Alert Test:")
    b_alert = engine.check_budget_alerts(current_spending=4800.0, monthly_limit=5000.0)
    if b_alert:
        print(f" * [{b_alert['severity']}] {b_alert['message']}")

    crit_alert = engine.check_budget_alerts(current_spending=5400.0, monthly_limit=5000.0)
    if crit_alert:
        print(f" * [{crit_alert['severity']}] {crit_alert['message']}")
