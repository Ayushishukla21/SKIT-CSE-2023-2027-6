"""Machine Learning Feature Engineering for SmartCart AI Price Monitoring.

Role: Ayushi (Data Engineering, ML Feature Engineering, ML Readiness)

Generates time-series features strictly without lookahead bias:
- prev_price: Previous observed price for product-platform series
- prev_recorded_at: Timestamp of previous observation
- price_change: Price difference from previous observation (price - prev_price)
- price_change_pct: Percentage change ((price - prev_price) / prev_price) * 100
- day_of_week: 0 (Monday) through 6 (Sunday)
- month: 1 through 12
- Preserves product_id, platform_id, canonical metadata, and original clean CSV.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Optional
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CLEAN_CSV = PROCESSED_DIR / "historical_prices_clean.csv"
ML_READY_CSV = PROCESSED_DIR / "ml_ready_prices.csv"


def generate_ml_features(clean_df: pd.DataFrame) -> pd.DataFrame:
    """Generate historical time-series features without data leakage.

    Rules:
    - Sorts records chronologically per product-platform combination.
    - Previous price features are isolated within (product_id, platform_id).
    - If available = False, price is NaN (never 0).
    - First observation of any series has NaN previous price and changes.
    """
    df = clean_df.copy()

    # 1. Ensure chronological ordering
    df["recorded_dt"] = pd.to_datetime(df["recorded_at"])
    df = df.sort_values(by=["product_id", "platform_id", "recorded_dt"]).reset_index(drop=True)

    # 2. Calendar features (strictly backward/current only)
    df["day_of_week"] = df["recorded_dt"].dt.dayofweek
    df["month"] = df["recorded_dt"].dt.month

    # Initialize feature containers
    prev_prices = []
    prev_timestamps = []
    price_changes = []
    price_change_pcts = []

    # Group strictly by (product_id, platform_id)
    grouped = df.groupby(["product_id", "platform_id"], sort=False)

    for (p_id, plat_id), group in grouped:
        last_valid_price: Optional[float] = None
        last_valid_ts: Optional[str] = None

        for _, row in group.iterrows():
            current_avail = bool(row["available"])
            current_price = row["price"] if (pd.notna(row["price"]) and current_avail) else None

            # Record previous state
            prev_prices.append(last_valid_price)
            prev_timestamps.append(last_valid_ts)

            # Calculate changes if both current and previous prices exist
            if current_price is not None and last_valid_price is not None and last_valid_price > 0:
                diff = round(float(current_price) - float(last_valid_price), 2)
                pct = round((diff / float(last_valid_price)) * 100, 2)
                price_changes.append(diff)
                price_change_pcts.append(pct)
            else:
                price_changes.append(np.nan)
                price_change_pcts.append(np.nan)

            # Update rolling state for subsequent observations ONLY
            if current_price is not None:
                last_valid_price = float(current_price)
                last_valid_ts = str(row["recorded_at"])

    df["prev_recorded_at"] = prev_timestamps
    df["prev_price"] = prev_prices
    df["price_change"] = price_changes
    df["price_change_pct"] = price_change_pcts

    # Clean up internal helper columns
    df = df.drop(columns=["recorded_dt"])

    # Column ordering
    ordered_cols = [
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
        "day_of_week",
        "month",
        "prev_recorded_at",
        "prev_price",
        "price_change",
        "price_change_pct",
    ]

    # Include discount & effective_price if present in clean dataset
    if "discount_amount" in df.columns:
        ordered_cols.append("discount_amount")
    if "effective_price" in df.columns:
        ordered_cols.append("effective_price")

    return df[ordered_cols]


def main() -> None:
    print("=" * 65)
    print("SmartCart AI: ML Feature Engineering (Ayushi)")
    print("=" * 65)

    if not CLEAN_CSV.exists():
        print(f"Error: {CLEAN_CSV} does not exist.")
        sys.exit(1)

    clean_df = pd.read_csv(CLEAN_CSV)
    print(f"Loaded clean historical dataset: {len(clean_df)} rows")

    ml_df = generate_ml_features(clean_df)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ml_df.to_csv(ML_READY_CSV, index=False)
    print(f"Saved ML-ready dataset to: {ML_READY_CSV}")
    print(f"Dataset shape: {ml_df.shape}")
    print("\nFeature Summary:")
    print(f"  - Total Rows: {len(ml_df)}")
    print(f"  - Non-null previous prices: {ml_df['prev_price'].notna().sum()}")
    print(f"  - Non-null price changes: {ml_df['price_change'].notna().sum()}")
    print(f"  - Unique products: {ml_df['product_id'].nunique()}")
    print(f"  - Unique platforms: {ml_df['platform_id'].nunique()}")
    print("\nSample Generated Features:")
    print(ml_df[["product_name", "platform", "recorded_at", "price", "prev_price", "price_change", "price_change_pct"]].head(10).to_string())


if __name__ == "__main__":
    main()
