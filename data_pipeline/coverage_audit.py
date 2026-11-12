"""Dataset coverage audit module for SmartCart AI.

Role: Ayushi (Data Engineering, Dataset Coverage Audit, ML Readiness)

Calculates observations per product-platform combination, verifies
temporal continuity across the 40-day observation window, and flags
combinations with insufficient observations or high stockout rates.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Dict, List, Tuple
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CLEAN_CSV = PROCESSED_DIR / "historical_prices_clean.csv"
COVERAGE_CSV = PROCESSED_DIR / "dataset_coverage_summary.csv"


def audit_coverage(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Audit observation counts and availability per product-platform combination."""
    # Ensure datetime parsing
    df = df.copy()
    df["recorded_dt"] = pd.to_datetime(df["recorded_at"])
    df["date"] = df["recorded_dt"].dt.date

    summary_rows: List[Dict[str, Any]] = []
    
    unique_dates = sorted(df["date"].unique())
    expected_days = len(unique_dates)

    # Group by product and platform
    grouped = df.groupby(["product_id", "product_name", "platform_id", "platform"])

    for (p_id, p_name, plat_id, plat_name), group in grouped:
        total_obs = len(group)
        avail_mask = group["available"].astype(str).str.lower().isin(["true", "1"])
        available_obs = int(avail_mask.sum())
        unavailable_obs = int((~avail_mask).sum())
        avail_rate = round((available_obs / total_obs) * 100, 1) if total_obs > 0 else 0.0

        min_date = group["recorded_at"].min()
        max_date = group["recorded_at"].max()
        distinct_dates = group["date"].nunique()
        missing_dates = expected_days - distinct_dates

        # Flag coverage adequacy
        if available_obs == 0:
            status = "INSUFFICIENT_OBSERVATIONS (100% Unavailable)"
        elif avail_rate < 80.0:
            status = "PARTIAL_COVERAGE"
        else:
            status = "COMPLETE"

        summary_rows.append({
            "product_id": p_id,
            "product_name": p_name,
            "platform_id": plat_id,
            "platform": plat_name,
            "total_observations": total_obs,
            "available_observations": available_obs,
            "unavailable_observations": unavailable_obs,
            "availability_rate_pct": avail_rate,
            "start_date": min_date,
            "end_date": max_date,
            "distinct_dates": distinct_dates,
            "missing_dates": missing_dates,
            "coverage_status": status,
        })

    coverage_df = pd.DataFrame(summary_rows)
    coverage_df = coverage_df.sort_values(by=["product_id", "platform_id"]).reset_index(drop=True)

    overall_metrics = {
        "total_records": len(df),
        "total_combinations": len(coverage_df),
        "total_products": df["product_id"].nunique(),
        "total_platforms": df["platform_id"].nunique(),
        "expected_dates": expected_days,
        "complete_coverage_combinations": int((coverage_df["coverage_status"] == "COMPLETE").sum()),
        "insufficient_data_combinations": int((coverage_df["available_observations"] == 0).sum()),
        "overall_available_rate_pct": round((df["available"].astype(str).str.lower().isin(["true", "1"]).sum() / len(df)) * 100, 1),
    }

    return coverage_df, overall_metrics


def main() -> None:
    print("=" * 65)
    print("SmartCart AI: Dataset Coverage Audit (Ayushi)")
    print("=" * 65)

    if not CLEAN_CSV.exists():
        print(f"Error: {CLEAN_CSV} does not exist. Run prepare_historical_data.py first.")
        sys.exit(1)

    df = pd.read_csv(CLEAN_CSV)
    coverage_df, metrics = audit_coverage(df)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    coverage_df.to_csv(COVERAGE_CSV, index=False)
    print(f"Coverage summary saved to: {COVERAGE_CSV}")
    print("\nOverall Metrics:")
    for key, val in metrics.items():
        print(f"  - {key}: {val}")

    print("\nSample Coverage Details (Per Combination):")
    print(coverage_df[["product_name", "platform", "total_observations", "available_observations", "availability_rate_pct", "coverage_status"]].to_string(index=False))

    insufficient = coverage_df[coverage_df["coverage_status"].str.startswith("INSUFFICIENT")]
    if not insufficient.empty:
        print("\nIdentified Insufficient Coverage Combinations:")
        for _, row in insufficient.iterrows():
            print(f"  * Product: {row['product_name']} on Platform: {row['platform']} -> {row['coverage_status']}")


if __name__ == "__main__":
    main()
