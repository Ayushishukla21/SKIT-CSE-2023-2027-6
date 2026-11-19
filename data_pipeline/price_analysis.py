"""Price analysis, volatility, and cheapest platform calculation module.

Role: Ayushi Shukla (23ESKCS039) - AI Lead, ML Prediction & Price Analysis

Computes:
- Historical price summary statistics (mean, min, max, std dev) per product & platform.
- Price volatility metrics (standard deviation and coefficient of variation).
- Identification of the cheapest platform per product across available observations.
- Detailed price changes over time.
- Handles out-of-stock / unavailable products without corrupting statistical metrics.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CLEAN_CSV = PROCESSED_DIR / "historical_prices_clean.csv"


def analyze_historical_prices(
    df: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Compute summary price stats, volatility, and cheapest platform per product."""
    if df is None:
        if not CLEAN_CSV.exists():
            raise FileNotFoundError(f"{CLEAN_CSV} does not exist")
        df = pd.read_csv(CLEAN_CSV)

    df = df.copy()
    if "recorded_at" in df.columns:
        df["recorded_at"] = pd.to_datetime(df["recorded_at"], errors="coerce", utc=True)

    # 1. Product catalog info for all 6 products & 4 platforms
    all_products = {
        1: ("Amul Taaza Milk", "Dairy"),
        2: ("Aashirvaad Atta", "Staples"),
        3: ("Tata Salt", "Staples"),
        4: ("Tata Tea", "Beverages"),
        5: ("Maggi 2-Minute Noodles", "Packaged Food"),
        6: ("Parle-G Biscuits", "Snacks"),
    }
    all_platforms = {
        1: "Blinkit",
        2: "Zepto",
        3: "Instamart",
        4: "Flipkart Minutes",
    }

    records: List[Dict[str, Any]] = []
    product_platform_means: Dict[int, Dict[str, float]] = {p: {} for p in all_products}

    for p_id, (p_name, category) in all_products.items():
        for plat_id, plat_name in all_platforms.items():
            sub = df[(df["product_id"] == p_id) & (df["platform_id"] == plat_id)]
            total_obs = len(sub)

            if total_obs == 0:
                avail_obs = 0
                valid_prices = pd.Series(dtype=float)
            else:
                avail_mask = sub["available"].astype(str).str.lower().isin(["true", "1", "yes"])
                valid_prices = sub.loc[avail_mask, "price"].dropna().astype(float)
                avail_obs = len(valid_prices)

            if avail_obs == 0:
                records.append({
                    "product_id": p_id,
                    "product_name": p_name,
                    "category": category,
                    "platform_id": plat_id,
                    "platform": plat_name,
                    "total_observations": total_obs,
                    "available_observations": 0,
                    "min_price": np.nan,
                    "max_price": np.nan,
                    "mean_price": np.nan,
                    "price_volatility_std": np.nan,
                    "volatility_cv_pct": np.nan,
                    "data_sufficiency": "INSUFFICIENT_DATA (0 available prices)",
                })
                continue

            min_p = round(float(valid_prices.min()), 2)
            max_p = round(float(valid_prices.max()), 2)
            mean_p = round(float(valid_prices.mean()), 2)
            std_p = round(float(valid_prices.std()), 2) if avail_obs > 1 else 0.0
            cv_pct = round((std_p / mean_p) * 100, 2) if mean_p > 0 else 0.0

            product_platform_means[p_id][plat_name] = mean_p

            records.append({
                "product_id": p_id,
                "product_name": p_name,
                "category": category,
                "platform_id": plat_id,
                "platform": plat_name,
                "total_observations": total_obs,
                "available_observations": avail_obs,
                "min_price": min_p,
                "max_price": max_p,
                "mean_price": mean_p,
                "price_volatility_std": std_p,
                "volatility_cv_pct": cv_pct,
                "data_sufficiency": "SUFFICIENT",
            })

    summary_df = pd.DataFrame(records)

    # Determine cheapest platform per product among available data
    cheapest_lookup: Dict[int, Tuple[str, float]] = {}
    for p_id, plat_dict in product_platform_means.items():
        if plat_dict:
            best_plat = min(plat_dict.items(), key=lambda x: x[1])
            cheapest_lookup[p_id] = best_plat
        else:
            cheapest_lookup[p_id] = ("None (All Unavailable)", np.nan)

    summary_df["cheapest_platform_for_product"] = summary_df["product_id"].map(
        lambda pid: cheapest_lookup[pid][0]
    )
    summary_df["cheapest_platform_avg_price"] = summary_df["product_id"].map(
        lambda pid: cheapest_lookup[pid][1]
    )

    overview = {
        "products_analyzed": len(all_products),
        "platforms_analyzed": len(all_platforms),
        "total_combinations": len(summary_df),
        "sufficient_data_combinations": int((summary_df["data_sufficiency"] == "SUFFICIENT").sum()),
        "insufficient_data_combinations": int((summary_df["data_sufficiency"] != "SUFFICIENT").sum()),
        "cheapest_platform_by_product": {
            all_products[pid][0]: cheapest_lookup[pid][0]
            for pid in all_products
        },
    }

    return summary_df, overview


def generate_price_reports():
    """Generate all analytical CSV files for SmartCart AI price monitoring."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(CLEAN_CSV)
    df["recorded_at"] = pd.to_datetime(df["recorded_at"], errors="coerce", utc=True)

    summary_df, overview = analyze_historical_prices(df)
    summary_df.to_csv(PROCESSED_DIR / "price_analysis_summary.csv", index=False)

    # 1. Average price by product and platform
    platform_summary = (
        df[df["available"].astype(str).str.lower().isin(["true", "1", "yes"])]
        .groupby(["product_id", "product_name", "platform_id", "platform"], as_index=False)
        .agg(
            average_price=("price", "mean"),
            minimum_price=("price", "min"),
            maximum_price=("price", "max"),
            observations=("price", "count"),
        )
    )
    platform_summary.to_csv(PROCESSED_DIR / "price_platform_summary.csv", index=False)

    # 2. Cheapest platform for each product
    cheapest_rows = []
    for p_id in sorted(df["product_id"].unique()):
        prod_sub = platform_summary[platform_summary["product_id"] == p_id]
        if not prod_sub.empty:
            min_row = prod_sub.loc[prod_sub["average_price"].idxmin()]
            cheapest_rows.append(min_row)
    if cheapest_rows:
        cheapest_platform = pd.DataFrame(cheapest_rows).sort_values("product_id")
        cheapest_platform.to_csv(PROCESSED_DIR / "cheapest_platform_by_product.csv", index=False)

    # 3. Price change over time
    df_sorted = df.sort_values(["product_id", "platform_id", "recorded_at"]).copy()
    groups = df_sorted.groupby(["product_id", "platform_id"])
    df_sorted["previous_price"] = groups["price"].shift(1)
    df_sorted["price_change"] = df_sorted["price"] - df_sorted["previous_price"]
    df_sorted["price_change_percent"] = (
        df_sorted["price_change"] / df_sorted["previous_price"] * 100
    )
    price_changes = df_sorted.dropna(subset=["previous_price"])
    price_changes.to_csv(PROCESSED_DIR / "price_changes.csv", index=False)

    # 4. Price volatility
    volatility = (
        df[df["available"].astype(str).str.lower().isin(["true", "1", "yes"])]
        .groupby(["product_id", "product_name", "platform"], as_index=False)
        .agg(
            average_price=("price", "mean"),
            price_std=("price", "std"),
            minimum_price=("price", "min"),
            maximum_price=("price", "max"),
        )
    )
    volatility["price_range"] = volatility["maximum_price"] - volatility["minimum_price"]
    volatility.to_csv(PROCESSED_DIR / "price_volatility.csv", index=False)

    print("===== PRICE ANALYSIS COMPLETE =====")
    print(f"Input rows: {len(df)}")
    print(f"Products: {df['product_id'].nunique()}")
    print(f"Platforms: {df['platform_id'].nunique()}")
    print("Created:")
    print("- price_platform_summary.csv")
    print("- cheapest_platform_by_product.csv")
    print("- price_changes.csv")
    print("- price_volatility.csv")
    print("- price_analysis_summary.csv")


if __name__ == "__main__":
    generate_price_reports()
