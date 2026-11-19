"""Smart Budget Planner for SmartCart AI.

Role: Ayushi Shukla (23ESKCS039) - AI Lead, ML Prediction, Smart Recommendations & Budget Planning
Sprint 5: Smart Budget Planner & Grocery Basket Optimization

Capabilities:
1. Accept user shopping basket with product IDs and quantities.
2. Evaluate total basket cost across all 4 quick-commerce platforms.
3. Handle platform-specific item availability (e.g., unavailable items flagged).
4. Identify optimal single platform for lowest total basket expenditure.
5. Compute multi-platform split basket for maximum possible cross-store savings.
6. Track budget utilization, remaining allowance, and budget deficit.
7. Provide actionable substitution and quantity-adjustment recommendations when over budget.
8. Validate inputs securely (positive budget, valid quantities, valid product catalog IDs).
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
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

# Canonical Catalog Definitions
PRODUCT_CATALOG: Dict[int, Dict[str, Any]] = {
    1: {"name": "Amul Taaza Milk", "brand": "Amul", "category": "Dairy", "pack": "1 L"},
    2: {"name": "Aashirvaad Atta", "brand": "Aashirvaad", "category": "Staples", "pack": "5 kg"},
    3: {"name": "Tata Salt", "brand": "Tata", "category": "Staples", "pack": "1 kg"},
    4: {"name": "Tata Tea", "brand": "Tata", "category": "Beverages", "pack": "250 g"},
    5: {"name": "Maggi 2-Minute Noodles", "brand": "Nestle", "category": "Packaged Food", "pack": "1 pack"},
    6: {"name": "Parle-G Biscuits", "brand": "Parle", "category": "Snacks", "pack": "1 pack"},
}

PLATFORM_CATALOG: Dict[int, str] = {
    1: "Blinkit",
    2: "Zepto",
    3: "Instamart",
    4: "Flipkart Minutes",
}


class SmartBudgetPlanner:
    """Grocery basket budget optimization and platform comparison engine."""

    def __init__(self, snapshot_df: Optional[pd.DataFrame] = None) -> None:
        """Initialize planner with latest price observations."""
        if snapshot_df is not None:
            self.snapshot_df = snapshot_df.copy()
        elif PROCESSED_PRICES_CSV.exists():
            self.snapshot_df = pd.read_csv(PROCESSED_PRICES_CSV)
        elif HISTORICAL_CLEAN_CSV.exists():
            hist = pd.read_csv(HISTORICAL_CLEAN_CSV).sort_values("recorded_at")
            self.snapshot_df = hist.groupby(["product_id", "platform_id"]).last().reset_index()
        else:
            self.snapshot_df = pd.DataFrame()

    def _validate_basket_and_budget(
        self, basket: List[Dict[str, Any]], monthly_budget: float
    ) -> None:
        """Thorough validation of user inputs."""
        # Validate budget
        if not isinstance(monthly_budget, (int, float, np.number)):
            raise TypeError(f"monthly_budget must be numeric, got {type(monthly_budget).__name__}")
        if monthly_budget <= 0 or np.isnan(monthly_budget):
            raise ValueError(f"monthly_budget must be a positive number greater than 0, got {monthly_budget}")

        # Validate basket
        if not isinstance(basket, list):
            raise TypeError(f"basket must be a list of items, got {type(basket).__name__}")
        if len(basket) == 0:
            raise ValueError("Shopping basket cannot be empty.")

        seen_products = set()
        for i, item in enumerate(basket):
            if not isinstance(item, dict):
                raise TypeError(f"Basket item at index {i} must be a dictionary, got {type(item).__name__}")
            if "product_id" not in item:
                raise ValueError(f"Basket item at index {i} missing 'product_id'")
            if "quantity" not in item:
                raise ValueError(f"Basket item at index {i} missing 'quantity'")

            p_id = item["product_id"]
            if not isinstance(p_id, (int, np.integer)) or p_id not in PRODUCT_CATALOG:
                raise ValueError(f"Invalid product_id: {p_id}. Must be one of {list(PRODUCT_CATALOG.keys())}")

            qty = item["quantity"]
            if not isinstance(qty, (int, np.integer)) or qty <= 0:
                raise ValueError(f"Quantity for product_id {p_id} must be a positive integer > 0, got {qty}")

            if p_id in seen_products:
                raise ValueError(f"Duplicate product_id {p_id} found in basket. Combine quantities into a single item.")
            seen_products.add(p_id)

    def _get_price(self, product_id: int, platform_id: int) -> Tuple[Optional[float], bool]:
        """Lookup price and availability for product on platform."""
        if self.snapshot_df.empty:
            return None, False

        match = self.snapshot_df[
            (self.snapshot_df["product_id"] == product_id)
            & (self.snapshot_df["platform_id"] == platform_id)
        ]
        if match.empty:
            return None, False

        row = match.iloc[0]
        is_avail = str(row.get("available", "")).lower() in ["true", "1", "yes"]
        price = row.get("price")
        if not is_avail or pd.isna(price) or float(price) <= 0:
            return None, False

        return round(float(price), 2), True

    def evaluate_basket_on_platform(
        self, basket: List[Dict[str, Any]], platform_id: int
    ) -> Dict[str, Any]:
        """Evaluate basket cost on a single quick-commerce platform."""
        platform_name = PLATFORM_CATALOG.get(platform_id, f"Platform {platform_id}")
        items_breakdown: List[Dict[str, Any]] = []
        total_cost = 0.0
        missing_products: List[Dict[str, Any]] = []

        for item in basket:
            p_id = item["product_id"]
            qty = item["quantity"]
            prod_meta = PRODUCT_CATALOG[p_id]
            unit_price, is_avail = self._get_price(p_id, platform_id)

            if is_avail and unit_price is not None:
                item_total = round(unit_price * qty, 2)
                total_cost += item_total
                items_breakdown.append({
                    "product_id": p_id,
                    "product_name": prod_meta["name"],
                    "brand": prod_meta["brand"],
                    "category": prod_meta["category"],
                    "quantity": qty,
                    "unit_price": unit_price,
                    "total_price": item_total,
                    "available": True,
                })
            else:
                missing_products.append({
                    "product_id": p_id,
                    "product_name": prod_meta["name"],
                    "quantity": qty,
                })
                items_breakdown.append({
                    "product_id": p_id,
                    "product_name": prod_meta["name"],
                    "brand": prod_meta["brand"],
                    "category": prod_meta["category"],
                    "quantity": qty,
                    "unit_price": None,
                    "total_price": None,
                    "available": False,
                })

        is_complete = (len(missing_products) == 0)
        return {
            "platform_id": platform_id,
            "platform_name": platform_name,
            "total_cost": round(total_cost, 2),
            "is_complete_basket": is_complete,
            "fulfilled_items_count": len(basket) - len(missing_products),
            "total_items_count": len(basket),
            "missing_products": missing_products,
            "items": items_breakdown,
        }

    def plan_budget(
        self,
        basket: List[Dict[str, Any]],
        monthly_budget: float,
        preferred_platform_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Comprehensive budget planning, platform optimization, and deficit recommendations."""
        self._validate_basket_and_budget(basket, monthly_budget)

        if preferred_platform_id is not None:
            if preferred_platform_id not in PLATFORM_CATALOG:
                raise ValueError(
                    f"Invalid preferred_platform_id: {preferred_platform_id}. "
                    f"Must be one of {list(PLATFORM_CATALOG.keys())}"
                )

        # 1. Evaluate basket across all platforms
        platform_evaluations: Dict[str, Dict[str, Any]] = {}
        complete_platforms: List[Dict[str, Any]] = []

        for plat_id in PLATFORM_CATALOG:
            eval_res = self.evaluate_basket_on_platform(basket, plat_id)
            platform_evaluations[eval_res["platform_name"]] = eval_res
            if eval_res["is_complete_basket"]:
                complete_platforms.append(eval_res)

        if not complete_platforms:
            # No single platform has all items available
            return {
                "status": "UNFULFILLABLE",
                "message": "No single platform has all requested items in stock.",
                "monthly_budget": round(monthly_budget, 2),
                "platforms_evaluated": platform_evaluations,
            }

        # 2. Find best (cheapest) and worst complete platform
        complete_platforms.sort(key=lambda x: x["total_cost"])
        optimal_platform = complete_platforms[0]
        most_expensive_platform = complete_platforms[-1]

        # Check if preferred platform was specified
        active_plan = optimal_platform
        if preferred_platform_id is not None:
            pref_name = PLATFORM_CATALOG[preferred_platform_id]
            pref_eval = platform_evaluations[pref_name]
            if pref_eval["is_complete_basket"]:
                active_plan = pref_eval

        # 3. Multi-platform Split Basket (cheapest item-by-item across ANY platform)
        split_items: List[Dict[str, Any]] = []
        split_total_cost = 0.0
        for item in basket:
            p_id = item["product_id"]
            qty = item["quantity"]
            prod_meta = PRODUCT_CATALOG[p_id]

            # Find cheapest available platform for this specific item
            cheapest_unit_price = float("inf")
            cheapest_item_plat = None
            for plat_id, plat_name in PLATFORM_CATALOG.items():
                u_price, avail = self._get_price(p_id, plat_id)
                if avail and u_price is not None and u_price < cheapest_unit_price:
                    cheapest_unit_price = u_price
                    cheapest_item_plat = plat_name

            item_cost = round(cheapest_unit_price * qty, 2)
            split_total_cost += item_cost
            split_items.append({
                "product_id": p_id,
                "product_name": prod_meta["name"],
                "quantity": qty,
                "best_platform": cheapest_item_plat,
                "unit_price": cheapest_unit_price,
                "total_price": item_cost,
            })

        split_total_cost = round(split_total_cost, 2)
        split_savings_vs_single = round(optimal_platform["total_cost"] - split_total_cost, 2)

        # 4. Budget Status & Calculations for Selected/Optimal Platform
        basket_total = active_plan["total_cost"]
        utilization_pct = round((basket_total / monthly_budget) * 100, 2)
        remaining_budget = round(monthly_budget - basket_total, 2)
        is_within_budget = basket_total <= monthly_budget
        deficit = round(max(0.0, basket_total - monthly_budget), 2)

        if utilization_pct <= 90.0:
            budget_status = "WITHIN_BUDGET"
        elif utilization_pct <= 100.0:
            budget_status = "NEAR_LIMIT"
        else:
            budget_status = "OVER_BUDGET"

        # Platform Savings
        platform_savings_inr = round(most_expensive_platform["total_cost"] - optimal_platform["total_cost"], 2)
        platform_savings_pct = (
            round((platform_savings_inr / most_expensive_platform["total_cost"]) * 100, 2)
            if most_expensive_platform["total_cost"] > 0 else 0.0
        )

        # 5. Smart Recommendations & Cost Savings Strategies
        recommendations: List[Dict[str, Any]] = []

        # Platform recommendation
        if active_plan["platform_id"] != optimal_platform["platform_id"]:
            switch_savings = round(active_plan["total_cost"] - optimal_platform["total_cost"], 2)
            recommendations.append({
                "type": "PLATFORM_SWITCH",
                "suggestion": (
                    f"Switch from {active_plan['platform_name']} to {optimal_platform['platform_name']} "
                    f"to save INR {switch_savings:.2f}."
                ),
                "potential_savings": switch_savings,
            })
        else:
            recommendations.append({
                "type": "OPTIMAL_PLATFORM",
                "suggestion": (
                    f"Order all items on {optimal_platform['platform_name']} for lowest single-cart cost: "
                    f"INR {optimal_platform['total_cost']:.2f} (saves INR {platform_savings_inr:.2f} vs {most_expensive_platform['platform_name']})."
                ),
                "potential_savings": platform_savings_inr,
            })

        # Split basket recommendation
        if split_savings_vs_single > 0:
            recommendations.append({
                "type": "MULTI_PLATFORM_SPLIT",
                "suggestion": (
                    f"Order across multiple stores (Blinkit + Zepto) to minimize cost to "
                    f"INR {split_total_cost:.2f}, saving an additional INR {split_savings_vs_single:.2f}."
                ),
                "potential_savings": split_savings_vs_single,
            })

        # Over-budget suggestions (Quantity reduction and substitutions)
        if not is_within_budget:
            # Sort items by highest total expenditure on active platform
            sorted_items = sorted(active_plan["items"], key=lambda x: x["total_price"], reverse=True)
            top_item = sorted_items[0]

            recommendations.append({
                "type": "BUDGET_RECOVERY_QUANTITY",
                "suggestion": (
                    f"Reduce quantity of {top_item['product_name']} from {top_item['quantity']} "
                    f"to {max(1, top_item['quantity'] - 1)} to save INR {top_item['unit_price']:.2f}."
                ),
                "potential_savings": top_item["unit_price"],
            })

            # Check if switching to optimal platform helps recover budget
            if active_plan["platform_id"] != optimal_platform["platform_id"]:
                if optimal_platform["total_cost"] <= monthly_budget:
                    recommendations.append({
                        "type": "BUDGET_RECOVERY_SWITCH",
                        "suggestion": (
                            f"Simply switching to {optimal_platform['platform_name']} brings your basket "
                            f"within budget (INR {optimal_platform['total_cost']:.2f} vs budget of INR {monthly_budget:.2f})!"
                        ),
                        "potential_savings": switch_savings,
                    })

        return {
            "status": "SUCCESS",
            "monthly_budget": round(monthly_budget, 2),
            "basket_total_cost": basket_total,
            "remaining_budget": remaining_budget,
            "budget_deficit": deficit,
            "budget_utilization_pct": utilization_pct,
            "is_within_budget": is_within_budget,
            "budget_status": budget_status,
            "selected_platform": active_plan["platform_name"],
            "optimal_platform": optimal_platform["platform_name"],
            "optimal_platform_cost": optimal_platform["total_cost"],
            "most_expensive_platform": most_expensive_platform["platform_name"],
            "most_expensive_platform_cost": most_expensive_platform["total_cost"],
            "platform_savings_inr": platform_savings_inr,
            "platform_savings_pct": platform_savings_pct,
            "split_cart_optimal_cost": split_total_cost,
            "split_cart_extra_savings": split_savings_vs_single,
            "items_breakdown": active_plan["items"],
            "platform_comparison": {
                name: {
                    "total_cost": data["total_cost"],
                    "is_complete": data["is_complete_basket"],
                    "missing_products": [p["product_name"] for p in data["missing_products"]],
                }
                for name, data in platform_evaluations.items()
            },
            "recommendations": recommendations,
        }


# Functional Helper APIs
def plan_budget(
    basket: List[Dict[str, Any]],
    monthly_budget: float,
    preferred_platform_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Helper function to plan budget and optimize grocery basket."""
    planner = SmartBudgetPlanner()
    return planner.plan_budget(
        basket=basket,
        monthly_budget=monthly_budget,
        preferred_platform_id=preferred_platform_id,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 65)
    print("SmartCart AI: Smart Budget Planner (Sprint 5 - Ayushi)")
    print("=" * 65)

    sample_basket = [
        {"product_id": 1, "quantity": 2},  # Amul Milk x 2
        {"product_id": 2, "quantity": 1},  # Aashirvaad Atta x 1
        {"product_id": 3, "quantity": 1},  # Tata Salt x 1
        {"product_id": 5, "quantity": 4},  # Maggi x 4
    ]
    budget_limit = 500.0

    planner = SmartBudgetPlanner()
    plan = planner.plan_budget(sample_basket, monthly_budget=budget_limit)

    print(f"\nBudget Limit: INR {plan['monthly_budget']:.2f}")
    print(f"Optimal Platform: {plan['optimal_platform']} (Total: INR {plan['optimal_platform_cost']:.2f})")
    print(f"Budget Utilization: {plan['budget_utilization_pct']}% | Status: {plan['budget_status']}")
    print(f"Remaining Budget: INR {plan['remaining_budget']:.2f}")
    print("\nPlatform Cost Comparison:")
    for plat, info in plan["platform_comparison"].items():
        comp_str = "Complete" if info["is_complete"] else f"Incomplete (missing: {info['missing_products']})"
        print(f" - {plat:16s}: INR {info['total_cost']:.2f} ({comp_str})")

    print("\nRecommendations:")
    for rec in plan["recommendations"]:
        print(f" * [{rec['type']}]: {rec['suggestion']}")
