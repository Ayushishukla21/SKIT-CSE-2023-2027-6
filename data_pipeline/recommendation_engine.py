"""Smart Recommendation Engine for SmartCart AI.

Role: Ayushi Shukla (23ESKCS039) - AI Lead, ML Prediction, Smart Recommendations & Budget Planning
Sprint 5: Smart Recommendation Engine & Deal Discovery

Capabilities:
1. Identify the cheapest platform for any canonical grocery product.
2. Calculate cross-platform price spreads, savings in INR and percentage.
3. Discover top deal products with highest price gaps across quick-commerce apps.
4. Detect favorable historical price trends (products currently below average price).
5. Generate end-to-end shopping recommendations (Buy Now vs Wait guidance).
6. Export structured recommendation reports to data/processed/smart_recommendations.csv.
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple
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
SUMMARY_CSV = PROCESSED_DIR / "price_platform_summary.csv"
RECOMMENDATIONS_CSV = PROCESSED_DIR / "smart_recommendations.csv"

# Canonical Products and Platforms
PRODUCT_CATALOG: Dict[int, Dict[str, Any]] = {
    1: {"name": "Amul Taaza Milk", "brand": "Amul", "category": "Dairy", "quantity": 1, "unit": "L"},
    2: {"name": "Aashirvaad Atta", "brand": "Aashirvaad", "category": "Staples", "quantity": 5, "unit": "kg"},
    3: {"name": "Tata Salt", "brand": "Tata", "category": "Staples", "quantity": 1, "unit": "kg"},
    4: {"name": "Tata Tea", "brand": "Tata", "category": "Beverages", "quantity": 250, "unit": "g"},
    5: {"name": "Maggi 2-Minute Noodles", "brand": "Nestle", "category": "Packaged Food", "quantity": 1, "unit": "pack"},
    6: {"name": "Parle-G Biscuits", "brand": "Parle", "category": "Snacks", "quantity": 1, "unit": "pack"},
}

PLATFORM_CATALOG: Dict[int, str] = {
    1: "Blinkit",
    2: "Zepto",
    3: "Instamart",
    4: "Flipkart Minutes",
}


class SmartRecommendationEngine:
    """Intelligent recommendation engine for cross-platform grocery price comparison."""

    def __init__(
        self,
        historical_df: Optional[pd.DataFrame] = None,
        snapshot_df: Optional[pd.DataFrame] = None,
        summary_df: Optional[pd.DataFrame] = None,
    ) -> None:
        """Initialize the recommendation engine with datasets or load from disk."""
        # 1. Historical dataset
        if historical_df is not None:
            self.historical_df = historical_df.copy()
        elif HISTORICAL_CLEAN_CSV.exists():
            self.historical_df = pd.read_csv(HISTORICAL_CLEAN_CSV)
        else:
            self.historical_df = pd.DataFrame()

        # 2. Latest price snapshot
        if snapshot_df is not None:
            self.snapshot_df = snapshot_df.copy()
        elif PROCESSED_PRICES_CSV.exists():
            self.snapshot_df = pd.read_csv(PROCESSED_PRICES_CSV)
        elif not self.historical_df.empty:
            # Fall back to latest observations per (product_id, platform_id)
            sorted_hist = self.historical_df.sort_values("recorded_at")
            self.snapshot_df = sorted_hist.groupby(["product_id", "platform_id"]).last().reset_index()
        else:
            self.snapshot_df = pd.DataFrame()

        # 3. Summary statistics
        if summary_df is not None:
            self.summary_df = summary_df.copy()
        elif SUMMARY_CSV.exists():
            self.summary_df = pd.read_csv(SUMMARY_CSV)
        else:
            self.summary_df = pd.DataFrame()

    def _validate_product_id(self, product_id: int) -> None:
        """Validate that product_id belongs to canonical catalog."""
        if not isinstance(product_id, (int, np.integer)):
            raise TypeError(f"product_id must be an integer, got {type(product_id).__name__}")
        if product_id not in PRODUCT_CATALOG:
            raise ValueError(
                f"Unknown product_id {product_id}. Valid IDs: {list(PRODUCT_CATALOG.keys())}"
            )

    def get_cheapest_platform(self, product_id: int) -> Dict[str, Any]:
        """Find the platform offering the lowest price for a canonical product."""
        self._validate_product_id(product_id)
        prod_meta = PRODUCT_CATALOG[product_id]

        if self.snapshot_df.empty:
            raise ValueError("No price observations available in snapshot dataset.")

        # Filter observations for this product
        prod_obs = self.snapshot_df[self.snapshot_df["product_id"] == product_id].copy()

        # Filter for available items with valid non-null prices > 0
        is_avail = prod_obs["available"].astype(str).str.lower().isin(["true", "1", "yes"])
        valid_obs = prod_obs[is_avail & prod_obs["price"].notna() & (prod_obs["price"] > 0)].copy()

        if valid_obs.empty:
            return {
                "product_id": product_id,
                "product_name": prod_meta["name"],
                "category": prod_meta["category"],
                "is_available": False,
                "cheapest_platform_id": None,
                "cheapest_platform": None,
                "cheapest_price": None,
                "highest_price": None,
                "potential_savings_inr": 0.0,
                "potential_savings_pct": 0.0,
                "platform_prices": {},
                "message": "Product currently unavailable on all monitored platforms.",
            }

        # Build mapping of platform -> price
        platform_prices: Dict[str, float] = {}
        for _, row in valid_obs.iterrows():
            plat_id = int(row["platform_id"])
            plat_name = PLATFORM_CATALOG.get(plat_id, f"Platform {plat_id}")
            platform_prices[plat_name] = round(float(row["price"]), 2)

        # Identify minimum and maximum prices
        min_row = valid_obs.sort_values("price").iloc[0]
        max_row = valid_obs.sort_values("price", ascending=False).iloc[0]

        cheapest_plat_id = int(min_row["platform_id"])
        cheapest_plat_name = PLATFORM_CATALOG.get(cheapest_plat_id, f"Platform {cheapest_plat_id}")
        cheapest_price = round(float(min_row["price"]), 2)

        highest_plat_id = int(max_row["platform_id"])
        highest_plat_name = PLATFORM_CATALOG.get(highest_plat_id, f"Platform {highest_plat_id}")
        highest_price = round(float(max_row["price"]), 2)

        savings_inr = round(highest_price - cheapest_price, 2)
        savings_pct = round((savings_inr / highest_price) * 100, 2) if highest_price > 0 else 0.0

        return {
            "product_id": product_id,
            "product_name": prod_meta["name"],
            "category": prod_meta["category"],
            "is_available": True,
            "cheapest_platform_id": cheapest_plat_id,
            "cheapest_platform": cheapest_plat_name,
            "cheapest_price": cheapest_price,
            "highest_platform_id": highest_plat_id,
            "highest_platform": highest_plat_name,
            "highest_price": highest_price,
            "potential_savings_inr": savings_inr,
            "potential_savings_pct": savings_pct,
            "platform_prices": platform_prices,
            "available_platforms_count": len(valid_obs),
            "message": (
                f"Cheapest on {cheapest_plat_name} at INR {cheapest_price:.2f}. "
                f"Save up to INR {savings_inr:.2f} ({savings_pct:.1f}%) vs {highest_plat_name}."
            ),
        }

    def get_cross_platform_savings(self, product_id: int) -> Dict[str, Any]:
        """Calculate detailed cross-platform savings metrics for a product."""
        cheapest_info = self.get_cheapest_platform(product_id)
        if not cheapest_info["is_available"]:
            return cheapest_info

        prices = list(cheapest_info["platform_prices"].values())
        avg_price = round(float(np.mean(prices)), 2)
        cheapest_price = cheapest_info["cheapest_price"]
        savings_vs_avg_inr = round(avg_price - cheapest_price, 2)
        savings_vs_avg_pct = round((savings_vs_avg_inr / avg_price) * 100, 2) if avg_price > 0 else 0.0

        cheapest_info["average_price"] = avg_price
        cheapest_info["savings_vs_average_inr"] = savings_vs_avg_inr
        cheapest_info["savings_vs_average_pct"] = savings_vs_avg_pct
        return cheapest_info

    def get_best_deal_products(
        self, top_n: int = 5, min_savings_pct: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Identify products offering the highest percentage savings across platforms."""
        deals: List[Dict[str, Any]] = []

        for p_id in PRODUCT_CATALOG:
            res = self.get_cross_platform_savings(p_id)
            if not res["is_available"] or res["available_platforms_count"] < 2:
                continue

            if res["potential_savings_pct"] >= min_savings_pct:
                deals.append({
                    "product_id": res["product_id"],
                    "product_name": res["product_name"],
                    "category": res["category"],
                    "cheapest_platform": res["cheapest_platform"],
                    "cheapest_price": res["cheapest_price"],
                    "highest_platform": res["highest_platform"],
                    "highest_price": res["highest_price"],
                    "potential_savings_inr": res["potential_savings_inr"],
                    "potential_savings_pct": res["potential_savings_pct"],
                    "deal_rating": (
                        "EXCELLENT" if res["potential_savings_pct"] >= 7.0
                        else "GOOD" if res["potential_savings_pct"] >= 3.0
                        else "MODERATE"
                    ),
                    "recommendation": (
                        f"Buy from {res['cheapest_platform']} to save "
                        f"INR {res['potential_savings_inr']:.2f} ({res['potential_savings_pct']:.1f}%)."
                    ),
                })

        # Rank deals descending by percentage savings, then INR savings
        deals.sort(key=lambda d: (d["potential_savings_pct"], d["potential_savings_inr"]), reverse=True)
        return deals[:top_n]

    def get_favorable_trend_products(
        self, drop_threshold_pct: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Identify products whose current price is noticeably lower than historical mean."""
        favorable: List[Dict[str, Any]] = []

        if self.historical_df.empty:
            return favorable

        # Calculate historical mean per product & platform
        hist = self.historical_df.copy()
        avail_mask = hist["available"].astype(str).str.lower().isin(["true", "1", "yes"])
        valid_hist = hist[avail_mask & hist["price"].notna() & (hist["price"] > 0)].copy()

        hist_means = (
            valid_hist.groupby(["product_id", "platform_id"])["price"]
            .agg(historical_mean="mean", historical_std="std", observation_count="count")
            .reset_index()
        )

        for _, row in hist_means.iterrows():
            p_id = int(row["product_id"])
            plat_id = int(row["platform_id"])
            h_mean = float(row["historical_mean"])

            # Find latest price
            snap_match = self.snapshot_df[
                (self.snapshot_df["product_id"] == p_id)
                & (self.snapshot_df["platform_id"] == plat_id)
            ]
            if snap_match.empty:
                continue

            snap_row = snap_row = snap_match.iloc[0]
            is_avail = str(snap_row.get("available", "")).lower() in ["true", "1", "yes"]
            if not is_avail or pd.isna(snap_row.get("price")):
                continue

            current_price = float(snap_row["price"])
            diff_inr = round(h_mean - current_price, 2)
            diff_pct = round((diff_inr / h_mean) * 100, 2) if h_mean > 0 else 0.0

            if diff_pct >= drop_threshold_pct:
                favorable.append({
                    "product_id": p_id,
                    "product_name": PRODUCT_CATALOG[p_id]["name"],
                    "platform_id": plat_id,
                    "platform": PLATFORM_CATALOG.get(plat_id, f"Platform {plat_id}"),
                    "current_price": round(current_price, 2),
                    "historical_mean": round(h_mean, 2),
                    "drop_inr": diff_inr,
                    "drop_pct": diff_pct,
                    "trend_advice": "FAVORABLE_BUY_NOW (Price is below historical average)",
                })

        favorable.sort(key=lambda x: x["drop_pct"], reverse=True)
        return favorable

    def get_product_recommendation(self, product_id: int) -> Dict[str, Any]:
        """Comprehensive recommendation combining cross-platform spread and trend."""
        savings = self.get_cross_platform_savings(product_id)
        if not savings["is_available"]:
            return {
                "product_id": product_id,
                "product_name": savings["product_name"],
                "decision": "UNAVAILABLE",
                "recommendation": "Product is currently out of stock on all platforms. Check back later.",
            }

        # Check historical price trend for the cheapest platform
        cheapest_plat_id = savings["cheapest_platform_id"]
        cheapest_price = savings["cheapest_price"]

        hist_sub = self.historical_df[
            (self.historical_df["product_id"] == product_id)
            & (self.historical_df["platform_id"] == cheapest_plat_id)
        ]
        avail_sub = hist_sub[
            hist_sub["available"].astype(str).str.lower().isin(["true", "1", "yes"])
        ]["price"].dropna()

        if len(avail_sub) >= 2:
            h_mean = float(avail_sub.mean())
            trend_diff = h_mean - cheapest_price
            trend_pct = (trend_diff / h_mean) * 100 if h_mean > 0 else 0.0
            if trend_pct >= 1.0:
                buy_timing = "BUY_NOW (Price is at or below historical dip)"
            elif trend_pct <= -2.0:
                buy_timing = "WAIT_IF_POSSIBLE (Price is near recent high)"
            else:
                buy_timing = "BUY_AS_NEEDED (Price is stable around historical normal)"
        else:
            h_mean = cheapest_price
            buy_timing = "BUY_AS_NEEDED (Limited trend data)"

        decision = "BUY_NOW" if savings["potential_savings_pct"] >= 5.0 or "BUY_NOW" in buy_timing else "BUY_AS_NEEDED"

        return {
            "product_id": product_id,
            "product_name": savings["product_name"],
            "category": savings["category"],
            "decision": decision,
            "recommended_platform": savings["cheapest_platform"],
            "best_price": cheapest_price,
            "highest_price": savings["highest_price"],
            "potential_savings_inr": savings["potential_savings_inr"],
            "potential_savings_pct": savings["potential_savings_pct"],
            "timing_advice": buy_timing,
            "all_prices": savings["platform_prices"],
            "summary": (
                f"Recommended: Purchase {savings['product_name']} on {savings['cheapest_platform']} "
                f"for INR {cheapest_price:.2f}. "
                f"You save INR {savings['potential_savings_inr']:.2f} ({savings['potential_savings_pct']:.1f}%) "
                f"compared to {savings['highest_platform']}."
            ),
        }

    def generate_all_recommendations(
        self, output_path: Optional[Path] = None
    ) -> pd.DataFrame:
        """Generate structured recommendation report for all catalog products and save to CSV."""
        rows: List[Dict[str, Any]] = []
        for p_id in PRODUCT_CATALOG:
            rec = self.get_product_recommendation(p_id)
            if rec.get("decision") == "UNAVAILABLE":
                rows.append({
                    "product_id": p_id,
                    "product_name": rec["product_name"],
                    "category": PRODUCT_CATALOG[p_id]["category"],
                    "decision": "UNAVAILABLE",
                    "recommended_platform": None,
                    "best_price": None,
                    "highest_price": None,
                    "potential_savings_inr": 0.0,
                    "potential_savings_pct": 0.0,
                    "timing_advice": "Out of stock",
                    "summary": rec["recommendation"],
                })
            else:
                rows.append({
                    "product_id": p_id,
                    "product_name": rec["product_name"],
                    "category": rec["category"],
                    "decision": rec["decision"],
                    "recommended_platform": rec["recommended_platform"],
                    "best_price": rec["best_price"],
                    "highest_price": rec["highest_price"],
                    "potential_savings_inr": rec["potential_savings_inr"],
                    "potential_savings_pct": rec["potential_savings_pct"],
                    "timing_advice": rec["timing_advice"],
                    "summary": rec["summary"],
                })

        df = pd.DataFrame(rows)
        save_path = output_path or RECOMMENDATIONS_CSV
        save_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(save_path, index=False)
        logger.info(f"Saved {len(df)} recommendations to {save_path}")
        return df


# Functional Helper APIs
def get_cheapest_platform(product_id: int) -> Dict[str, Any]:
    """Helper function to find cheapest platform for a product."""
    engine = SmartRecommendationEngine()
    return engine.get_cheapest_platform(product_id)


def get_best_deals(top_n: int = 5) -> List[Dict[str, Any]]:
    """Helper function to find top deals."""
    engine = SmartRecommendationEngine()
    return engine.get_best_deal_products(top_n=top_n)


def generate_recommendations() -> pd.DataFrame:
    """Helper function to generate and save all recommendations."""
    engine = SmartRecommendationEngine()
    return engine.generate_all_recommendations()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 65)
    print("SmartCart AI: Smart Recommendation Engine (Sprint 5 - Ayushi)")
    print("=" * 65)
    engine = SmartRecommendationEngine()
    recs_df = engine.generate_all_recommendations()
    print(f"\nGenerated recommendations for {len(recs_df)} products:")
    for _, r in recs_df.iterrows():
        print(f" * [{r['product_name']}] -> {r['decision']} on {r['recommended_platform']} (INR {r['best_price']}) | Savings: INR {r['potential_savings_inr']} ({r['potential_savings_pct']}%)")
    print(f"\nTop Deals:")
    for d in engine.get_best_deal_products():
        print(f" * {d['product_name']}: {d['recommendation']}")
