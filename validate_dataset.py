#!/usr/bin/env python3
"""Dataset validation script for SmartCart AI historical price data.

Sprint: Sprint 3 / October Week 2
Role: Ayushi (Data Engineering, Dataset Validation, ML Readiness)

Checks:
- Required columns exist
- No invalid negative or zero prices
- No duplicate product/platform/timestamp observations
- Unavailable products do not have numeric price (must be null/NaN, not 0)
- Valid platform IDs (1 to 4)
- Valid product IDs (1 to 6)
- Timestamps are parseable ISO 8601 UTC
- Dataset is sorted correctly (product_id, platform_id, recorded_at)
- No unexpected nulls in required identifiers
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List, Tuple
import pandas as pd

REQUIRED_COLUMNS = [
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
]

NON_NULL_IDENTIFIERS = [
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

VALID_PRODUCT_IDS = {1, 2, 3, 4, 5, 6}
VALID_PLATFORM_IDS = {1, 2, 3, 4}


def validate_historical_dataset(csv_path: Path) -> Tuple[bool, Dict[str, Any], List[str]]:
    """Validate historical dataset and return status, summary metrics, and issues."""
    issues: List[str] = []

    if not csv_path.exists():
        return False, {}, [f"File not found: {csv_path}"]

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        return False, {}, [f"Failed to parse CSV with Pandas: {exc}"]

    # 1. Required columns check
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        issues.append(f"Missing required columns: {', '.join(missing_cols)}")

    # 2. Check for unexpected nulls in identifiers
    unexpected_nulls = 0
    for col in NON_NULL_IDENTIFIERS:
        if col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                issues.append(f"Unexpected nulls in identifier column '{col}': {null_count}")
                unexpected_nulls += null_count

    # 3. Product IDs validation
    if "product_id" in df.columns:
        invalid_pids = set(df["product_id"].dropna().unique()) - VALID_PRODUCT_IDS
        if invalid_pids:
            issues.append(f"Invalid product IDs found: {invalid_pids}")

    # 4. Platform IDs validation
    if "platform_id" in df.columns:
        invalid_plat_ids = set(df["platform_id"].dropna().unique()) - VALID_PLATFORM_IDS
        if invalid_plat_ids:
            issues.append(f"Invalid platform IDs found: {invalid_plat_ids}")

    # 5. Duplicates on (product_id, platform_id, recorded_at)
    duplicate_rows = 0
    if {"product_id", "platform_id", "recorded_at"}.issubset(df.columns):
        duplicate_mask = df.duplicated(subset=["product_id", "platform_id", "recorded_at"], keep=False)
        duplicate_rows = int(duplicate_mask.sum())
        if duplicate_rows > 0:
            issues.append(f"Found {duplicate_rows} duplicate observations")

    # 6. Availability and Price validation
    invalid_prices = 0
    if {"available", "price"}.issubset(df.columns):
        # Convert boolean
        avail_series = df["available"].astype(str).str.lower().isin(["true", "1"])
        
        # Unavailable products must not have a numeric price (must be NaN/blank)
        unavail_with_price = df[~avail_series & df["price"].notna()]
        if len(unavail_with_price) > 0:
            issues.append(
                f"Unavailable products have numeric price in {len(unavail_with_price)} rows (must be NULL/NaN, not 0)"
            )
            invalid_prices += len(unavail_with_price)

        numeric_prices = pd.to_numeric(df["price"], errors="coerce")

        # Available products must have positive numeric price
        avail_without_price = df[avail_series & (df["price"].isna() | numeric_prices.isna())]
        if len(avail_without_price) > 0:
            issues.append(f"Available products missing valid numeric price in {len(avail_without_price)} rows")
            invalid_prices += len(avail_without_price)

        # Negative or zero prices
        non_positive_prices = df[avail_series & numeric_prices.notna() & (numeric_prices <= 0)]
        if len(non_positive_prices) > 0:
            issues.append(f"Non-positive prices found in {len(non_positive_prices)} rows")
            invalid_prices += len(non_positive_prices)

    # 7. Timestamp validation
    timestamps_parseable = True
    if "recorded_at" in df.columns:
        for idx, ts in enumerate(df["recorded_at"]):
            try:
                ts_str = str(ts).strip()
                if not ts_str.endswith("Z"):
                    raise ValueError("Must end with Z")
                datetime.fromisoformat(ts_str[:-1] + "+00:00")
            except Exception:
                timestamps_parseable = False
                issues.append(f"Invalid timestamp at row {idx + 2}: '{ts}'")
                break

    # 8. Sorting check (product_id, platform_id, recorded_at)
    is_sorted = True
    if {"product_id", "platform_id", "recorded_at"}.issubset(df.columns):
        sorted_df = df.sort_values(by=["product_id", "platform_id", "recorded_at"]).reset_index(drop=True)
        current_df = df[["product_id", "platform_id", "recorded_at"]].reset_index(drop=True)
        if not current_df.equals(sorted_df[["product_id", "platform_id", "recorded_at"]]):
            is_sorted = False
            issues.append("Dataset is not sorted by (product_id, platform_id, recorded_at)")

    # 9. Additional checks if ML-ready features are present
    if "day_of_week" in df.columns:
        invalid_dows = df[~df["day_of_week"].isin(list(range(7)))]
        if len(invalid_dows) > 0:
            issues.append(f"Invalid day_of_week found in {len(invalid_dows)} rows (must be 0..6)")

    if "month" in df.columns:
        invalid_months = df[~df["month"].isin(list(range(1, 13)))]
        if len(invalid_months) > 0:
            issues.append(f"Invalid month found in {len(invalid_months)} rows (must be 1..12)")

    if "prev_price" in df.columns:
        # prev_price should never be negative or zero when present
        invalid_prev = df[df["prev_price"].notna() & (df["prev_price"] <= 0)]
        if len(invalid_prev) > 0:
            issues.append(f"Invalid non-positive prev_price found in {len(invalid_prev)} rows")

    if {"price", "prev_price", "price_change"}.issubset(df.columns):
        # Verify arithmetic consistency where both prices exist
        calc_check = df[df["price"].notna() & df["prev_price"].notna() & df["price_change"].notna()].copy()
        diff = (calc_check["price"] - calc_check["prev_price"] - calc_check["price_change"]).abs()
        inconsistent_changes = calc_check[diff > 0.02]
        if len(inconsistent_changes) > 0:
            issues.append(f"Price change mismatch found in {len(inconsistent_changes)} rows")

    # Summary metrics
    rows_count = len(df)
    products_count = int(df["product_id"].nunique()) if "product_id" in df.columns else 0
    platforms_count = int(df["platform_id"].nunique()) if "platform_id" in df.columns else 0
    min_date = df["recorded_at"].min() if "recorded_at" in df.columns else "N/A"
    max_date = df["recorded_at"].max() if "recorded_at" in df.columns else "N/A"
    
    # Missing values across whole DataFrame
    total_missing_values = int(df.isna().sum().sum())
    
    summary = {
        "Rows": rows_count,
        "Products": products_count,
        "Platforms": platforms_count,
        "Date range": f"{min_date} to {max_date}",
        "Missing values": total_missing_values,
        "Duplicate rows": duplicate_rows,
        "Invalid prices": invalid_prices,
        "Sorted correctly": is_sorted,
        "Timestamps parseable": timestamps_parseable,
    }

    status = (len(issues) == 0)
    return status, summary, issues


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    default_csv = base_dir / "data" / "processed" / "historical_prices_clean.csv"

    if len(sys.argv) > 1:
        target_csv = Path(sys.argv[1])
    else:
        target_csv = default_csv

    print(f"Validating dataset: {target_csv}")
    print("-" * 50)

    passed, summary, issues = validate_historical_dataset(target_csv)

    print(f"Rows: {summary.get('Rows', 0)}")
    print(f"Products: {summary.get('Products', 0)}")
    print(f"Platforms: {summary.get('Platforms', 0)}")
    print(f"Date range: {summary.get('Date range', 'N/A')}")
    print(f"Missing values: {summary.get('Missing values', 0)} (expected for unavailable item prices)")
    print(f"Duplicate rows: {summary.get('Duplicate rows', 0)}")
    print(f"Invalid prices: {summary.get('Invalid prices', 0)}")
    print(f"Validation status: {'PASS' if passed else 'FAIL'}")

    if not passed:
        print("\nValidation Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("\nAll dataset integrity and ML-readiness constraints satisfied.")
        sys.exit(0)


if __name__ == "__main__":
    main()
