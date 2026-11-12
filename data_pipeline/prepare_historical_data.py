"""Historical price dataset generator and cleaning pipeline for SmartCart AI.

Sprint: Sprint 3 / October Week 2
Role: Ayushi (Data Engineering, Dataset Preparation, ML Readiness)

Features:
1. Generates realistic historical raw data (DEMO / HISTORICAL SIMULATION)
   spanning 40 days (2026-09-01 to 2026-10-10) for 6 canonical products
   across 4 quick-commerce platforms (Blinkit, Zepto, Instamart, Flipkart Minutes).
2. Introduces realistic market dynamics (weekend discounts, stockouts,
   price shifts) along with simulated ingestion noise (varying titles,
   inconsistent platform casing, currency symbols, and test edge cases).
3. Cleans, normalizes, deduplicates, and validates the dataset.
4. Outputs:
   - data/raw/historical_prices_raw.csv
   - data/processed/historical_prices_clean.csv
   - data/processed/product_mapping.csv
   - data/processed/historical_rejected_records.csv
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
import random
import sys
from typing import Any, Dict, List, Tuple
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from data_pipeline.canonical_matcher import (
    CANONICAL_PRODUCTS,
    generate_mapping_dataframe,
    match_product,
)
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

PLATFORMS = [
    {"id": 1, "name": "Blinkit", "aliases": ["blinkit", "Blinkit", " blinkit "]},
    {"id": 2, "name": "Zepto", "aliases": ["zepto", "ZEpto", "Zepto "]},
    {"id": 3, "name": "Instamart", "aliases": ["instamart", "Instamart", " Swiggy Instamart "]},
    {"id": 4, "name": "Flipkart Minutes", "aliases": ["flipkart minutes", "Flipkart Minutes", "Flipkart_Minutes"]},
]

# Baseline prices from existing data/prices.csv
BASE_PRICES = {
    # product_id: {platform_id: base_price}
    1: {1: 68.0, 2: 65.0, 3: 70.0, 4: 67.0},   # Amul Taaza Milk 1L
    2: {1: 265.0, 2: 259.0, 3: 272.0, 4: 262.0}, # Aashirvaad Atta 5kg
    3: {1: 28.0, 2: 27.0, 3: 29.0, 4: 28.0},    # Tata Salt 1kg
    4: {1: 145.0, 2: 142.0, 3: 148.0, 4: None}, # Tata Tea 250g (Flipkart Minutes unavailable)
    5: {1: 14.0, 2: 14.0, 3: 15.0, 4: 14.0},    # Maggi 2-Min Noodles 70g
    6: {1: 25.0, 2: 24.0, 3: 24.0, 4: 26.0},    # Parle-G Biscuits 250g
}

RAW_TITLE_TEMPLATES = {
    1: [
        "Amul Taaza Milk 1L",
        "Amul Taaza Milk - 1 Litre",
        "Amul Taaza Milk 1 L",
        "Amul Taaza Fresh Toned Milk (1 L)",
        "Amul Taaza Toned Milk Pouch (1 Litre)",
    ],
    2: [
        "Aashirvaad Atta 5kg",
        "Aashirvaad Superior MP Atta 5 kg",
        "Aashirvaad Whole Wheat Atta 5kg",
        "Aashirvaad Shudh Chakki Atta (5 kg)",
    ],
    3: [
        "Tata Salt 1kg",
        "Tata Iodized Salt 1 kg",
        "Tata Salt - 1kg Pouch",
        "Tata Vacuum Evaporated Iodized Salt (1 kg)",
    ],
    4: [
        "Tata Tea 250g",
        "Tata Tea Premium 250 g",
        "Tata Premium Tea (250g)",
        "Tata Tea Gold Leaf Tea 250 g",
    ],
    5: [
        "Maggi 2-Minute Noodles 70g",
        "Maggi 2-Minute Masala Noodles 70 g",
        "Maggi Masala 2 Minute Instant Noodles 70g",
        "Maggi 2-Minute Instant Noodles - 70 g",
    ],
    6: [
        "Parle-G Biscuits 250g",
        "Parle-G Original Gluco Biscuits 250 g",
        "Parle-G Gluco Biscuits - 250g",
        "Parle G Glucose Biscuits (250 g)",
    ],
}


def generate_raw_historical_dataset(
    start_date: str = "2026-09-01",
    days: int = 40,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Generate simulated historical raw price observations across 40 days.

    Includes realistic price variations, weekend promotional discounts,
    temporary stockouts, and simulated ingestion noise.
    """
    random.seed(seed)
    start_dt = datetime.fromisoformat(f"{start_date}T10:00:00+00:00")
    raw_records: List[Dict[str, Any]] = []

    for day_offset in range(days):
        current_date = start_dt + timedelta(days=day_offset)
        timestamp_str = current_date.isoformat().replace("+00:00", "Z")
        is_weekend = current_date.weekday() in (5, 6)

        for prod in CANONICAL_PRODUCTS:
            p_id = prod["id"]
            p_name = prod["name"]
            p_brand = prod["brand"]
            p_cat = prod["category"]
            p_qty = prod["quantity"]
            p_unit = prod["unit"]

            for plat in PLATFORMS:
                plat_id = plat["id"]
                plat_name = plat["name"]
                base_p = BASE_PRICES[p_id].get(plat_id)

                # Determine availability
                # Product 4 on Flipkart Minutes is unavailable most days (as per project baseline)
                if p_id == 4 and plat_id == 4:
                    available = False
                elif p_id == 5 and plat_id == 2 and day_offset in (17, 18):
                    # Temporary stockout for Maggi on Zepto mid-September
                    available = False
                elif p_id == 2 and plat_id == 3 and day_offset == 25:
                    # Single-day stockout for Atta on Instamart
                    available = False
                else:
                    available = True

                # Determine price & discount
                if not available:
                    price_val = ""
                    discount_val = ""
                else:
                    # Add subtle realistic fluctuation (±2.5%)
                    fluctuation = (random.random() - 0.5) * 0.05 * (base_p or 50.0)
                    price = round((base_p or 50.0) + fluctuation, 2)

                    # Weekend discount offer
                    if is_weekend and random.random() < 0.6:
                        if p_id == 2:  # Atta: ₹10 to ₹15 off
                            discount_val = round(random.choice([10.0, 12.0, 15.0]), 2)
                        elif p_id in (1, 4):  # Milk or Tea: ₹2 to ₹5 off
                            discount_val = round(random.choice([2.0, 3.0, 5.0]), 2)
                        else:  # Biscuits / Salt / Noodles: ₹1 to ₹2 off
                            discount_val = round(random.choice([1.0, 2.0]), 2)
                    else:
                        discount_val = 0.0

                    # Simulate raw price format with ₹ symbol or string padding
                    if random.random() < 0.5:
                        price_val = f"₹{price:.2f}"
                    elif random.random() < 0.8:
                        price_val = f"{price:.2f}"
                    else:
                        price_val = f" {price:.2f} "

                # Choose raw title variant
                title_template = random.choice(RAW_TITLE_TEMPLATES[p_id])
                # Randomize platform casing
                raw_plat_alias = random.choice(plat["aliases"])

                # Unit variation
                unit_variants = {
                    "L": ["L", "litre", "Litres", "l"],
                    "kg": ["kg", "KG", "kilogram", "kgs"],
                    "g": ["g", "grams", "gm", "g"],
                }
                raw_unit = random.choice(unit_variants.get(p_unit, [p_unit]))

                raw_records.append({
                    "product_id": str(p_id),
                    "product_name": title_template,
                    "brand": p_brand,
                    "category": p_cat,
                    "platform_id": str(plat_id),
                    "platform": raw_plat_alias,
                    "price": price_val,
                    "currency": "INR",
                    "available": "true" if available else "false",
                    "recorded_at": timestamp_str,
                    "quantity": str(p_qty),
                    "unit": raw_unit,
                    "discount_amount": str(discount_val) if discount_val != "" else "",
                })

    # Introduce deliberate edge cases to demonstrate cleaning and validation
    # 1. Duplicate observations
    raw_records.append(dict(raw_records[5]))
    raw_records.append(dict(raw_records[42]))

    # 2. Negative price
    raw_records.append({
        "product_id": "1",
        "product_name": "Amul Taaza Milk 1L",
        "brand": "Amul",
        "category": "Dairy",
        "platform_id": "1",
        "platform": "Blinkit",
        "price": "-68.00",
        "currency": "INR",
        "available": "true",
        "recorded_at": "2026-09-15T10:00:00Z",
        "quantity": "1",
        "unit": "L",
        "discount_amount": "",
    })

    # 3. Non-numeric price
    raw_records.append({
        "product_id": "2",
        "product_name": "Aashirvaad Atta 5kg",
        "brand": "Aashirvaad",
        "category": "Staples",
        "platform_id": "2",
        "platform": "Zepto",
        "price": "INVALID_PRICE",
        "currency": "INR",
        "available": "true",
        "recorded_at": "2026-09-16T10:00:00Z",
        "quantity": "5",
        "unit": "kg",
        "discount_amount": "",
    })

    # 4. Unavailable product erroneously containing price in raw feed
    raw_records.append({
        "product_id": "4",
        "product_name": "Tata Tea 250g",
        "brand": "Tata",
        "category": "Beverages",
        "platform_id": "4",
        "platform": "Flipkart Minutes",
        "price": "145.00",
        "currency": "INR",
        "available": "false",
        "recorded_at": "2026-09-17T10:00:00Z",
        "quantity": "250",
        "unit": "g",
        "discount_amount": "",
    })

    # 5. Invalid platform
    raw_records.append({
        "product_id": "3",
        "product_name": "Tata Salt 1kg",
        "brand": "Tata",
        "category": "Staples",
        "platform_id": "99",
        "platform": "Unknown Grocery",
        "price": "28.00",
        "currency": "INR",
        "available": "true",
        "recorded_at": "2026-09-18T10:00:00Z",
        "quantity": "1",
        "unit": "kg",
        "discount_amount": "",
    })

    return raw_records


def clean_historical_data(
    raw_records: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Clean, normalize, deduplicate, and validate raw historical observations.

    Rules:
    - Deduplicates on composite key (product_id, platform_id, recorded_at).
    - If available = false: price is None / NaN (never ₹0).
    - Filters out negative, zero, or corrupt prices.
    - Normalizes platform names and IDs (1..4).
    - Normalizes product names, brands, categories, and units using canonical matcher.
    - Computes effective_price = price - discount_amount when available.
    - Sorts records chronologically and hierarchically by (product_id, platform_id, recorded_at).
    """
    clean_records: List[Dict[str, Any]] = []
    rejected_records: List[Dict[str, Any]] = []

    seen_keys = set()
    platform_name_lookup = {
        "blinkit": (1, "Blinkit"),
        "zepto": (2, "Zepto"),
        "instamart": (3, "Instamart"),
        "swiggy instamart": (3, "Instamart"),
        "flipkart minutes": (4, "Flipkart Minutes"),
        "flipkart_minutes": (4, "Flipkart Minutes"),
    }

    for row_idx, row in enumerate(raw_records, start=1):
        # 1. Platform validation and normalization
        raw_platform = str(row.get("platform", "")).strip().lower()
        if raw_platform not in platform_name_lookup:
            rejected_records.append({
                "row_number": row_idx,
                "reason": f"Invalid platform: {row.get('platform')}",
                "raw_data": str(row),
            })
            continue
        plat_id, canonical_plat_name = platform_name_lookup[raw_platform]

        # 2. Product matching and normalization
        raw_title = str(row.get("product_name", "")).strip()
        matched_prod = match_product(raw_title)
        if not matched_prod:
            # Fallback to product_id if provided
            try:
                p_id_fallback = int(str(row.get("product_id", "")).strip())
                matched_prod = next((p for p in CANONICAL_PRODUCTS if p["id"] == p_id_fallback), None)
                if matched_prod:
                    matched_prod = {
                        "canonical_product_id": matched_prod["id"],
                        "canonical_name": matched_prod["name"],
                        "brand": matched_prod["brand"],
                        "category": matched_prod["category"],
                        "quantity": matched_prod["quantity"],
                        "unit": matched_prod["unit"],
                    }
            except (ValueError, TypeError):
                matched_prod = None

        if not matched_prod:
            rejected_records.append({
                "row_number": row_idx,
                "reason": f"Product could not be matched to canonical catalog: {raw_title}",
                "raw_data": str(row),
            })
            continue

        prod_id = matched_prod["canonical_product_id"]

        # 3. Timestamp normalization
        raw_ts = str(row.get("recorded_at", "")).strip()
        try:
            if raw_ts.endswith("Z"):
                parsed_ts = datetime.fromisoformat(raw_ts[:-1] + "+00:00")
            else:
                parsed_ts = datetime.fromisoformat(raw_ts)
            norm_ts = parsed_ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except Exception:
            rejected_records.append({
                "row_number": row_idx,
                "reason": f"Invalid ISO 8601 timestamp: {raw_ts}",
                "raw_data": str(row),
            })
            continue

        # 4. Duplicate check on (product_id, platform_id, recorded_at)
        comp_key = (prod_id, plat_id, norm_ts)
        if comp_key in seen_keys:
            rejected_records.append({
                "row_number": row_idx,
                "reason": f"Duplicate observation for {comp_key}",
                "raw_data": str(row),
            })
            continue
        seen_keys.add(comp_key)

        # 5. Availability parsing
        raw_avail = str(row.get("available", "")).strip().lower()
        if raw_avail not in ("true", "false"):
            rejected_records.append({
                "row_number": row_idx,
                "reason": f"Invalid boolean availability: {row.get('available')}",
                "raw_data": str(row),
            })
            continue
        is_available = (raw_avail == "true")

        # 6. Price parsing and validation
        raw_price_str = str(row.get("price", "")).strip()
        if raw_price_str.startswith("₹"):
            raw_price_str = raw_price_str[1:].strip()

        if is_available:
            try:
                price_val = float(raw_price_str)
                if price_val <= 0:
                    rejected_records.append({
                        "row_number": row_idx,
                        "reason": f"Price must be positive when available, found: {price_val}",
                        "raw_data": str(row),
                    })
                    continue
            except (ValueError, TypeError):
                rejected_records.append({
                    "row_number": row_idx,
                    "reason": f"Unparseable price for available item: '{raw_price_str}'",
                    "raw_data": str(row),
                })
                continue
        else:
            # When available is false, price MUST be None/NaN, NOT 0 and NOT a numeric price
            if raw_price_str not in ("", "none", "nan", "null"):
                rejected_records.append({
                    "row_number": row_idx,
                    "reason": f"Unavailable product must not contain a price. Found: '{raw_price_str}'",
                    "raw_data": str(row),
                })
                continue
            price_val = None

        # 7. Discount & Effective Price
        raw_disc_str = str(row.get("discount_amount", "")).strip()
        if raw_disc_str.startswith("₹"):
            raw_disc_str = raw_disc_str[1:].strip()

        if raw_disc_str not in ("", "none", "nan", "null"):
            try:
                discount_val = max(0.0, float(raw_disc_str))
            except (ValueError, TypeError):
                discount_val = 0.0
        else:
            discount_val = 0.0

        if is_available and price_val is not None:
            effective_price = round(max(0.0, price_val - discount_val), 2)
            final_price = round(price_val, 2)
            final_discount = round(discount_val, 2)
        else:
            effective_price = None
            final_price = None
            final_discount = None

        clean_records.append({
            "product_id": prod_id,
            "product_name": matched_prod["canonical_name"],
            "brand": matched_prod["brand"],
            "category": matched_prod["category"],
            "platform_id": plat_id,
            "platform": canonical_plat_name,
            "price": final_price,
            "currency": "INR",
            "available": is_available,
            "recorded_at": norm_ts,
            "quantity": matched_prod["quantity"],
            "unit": matched_prod["unit"],
            "discount_amount": final_discount,
            "effective_price": effective_price,
        })

    # Hierarchical sort by product_id, platform_id, recorded_at
    clean_records.sort(
        key=lambda r: (r["product_id"], r["platform_id"], r["recorded_at"])
    )

    return clean_records, rejected_records


def main() -> None:
    """Execute historical data preparation, cleaning, and persistence."""
    print("=" * 60)
    print("SmartCart AI: Preparing Historical Price Dataset (Ayushi)")
    print("=" * 60)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Generate Raw Historical Dataset
    print("[1/4] Generating raw historical demo observations...")
    raw_records = generate_raw_historical_dataset(
        start_date="2026-09-01",
        days=40,
        seed=42,
    )
    raw_csv_path = RAW_DIR / "historical_prices_raw.csv"

    raw_fieldnames = [
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
        "discount_amount",
    ]

    with open(raw_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=raw_fieldnames)
        writer.writeheader()
        writer.writerows(raw_records)
    print(f"      Saved raw records ({len(raw_records)} rows) to: {raw_csv_path}")

    # 2. Clean and Normalize Dataset
    print("[2/4] Cleaning, normalizing, and deduplicating records...")
    clean_records, rejected_records = clean_historical_data(raw_records)

    clean_csv_path = PROCESSED_DIR / "historical_prices_clean.csv"
    clean_fieldnames = [
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
        "discount_amount",
        "effective_price",
    ]

    with open(clean_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=clean_fieldnames)
        writer.writeheader()
        writer.writerows(clean_records)
    print(f"      Saved clean records ({len(clean_records)} rows) to: {clean_csv_path}")

    # Save rejection log
    rejected_csv_path = PROCESSED_DIR / "historical_rejected_records.csv"
    with open(rejected_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["row_number", "reason", "raw_data"])
        writer.writeheader()
        writer.writerows(rejected_records)
    print(f"      Saved rejected records ({len(rejected_records)} rows) to: {rejected_csv_path}")

    # 3. Generate Product Mapping CSV
    print("[3/4] Generating cross-platform product mapping dictionary...")
    mapping_df = generate_mapping_dataframe()
    mapping_csv_path = PROCESSED_DIR / "product_mapping.csv"
    mapping_df.to_csv(mapping_csv_path, index=False)
    print(f"      Saved cross-platform mappings ({len(mapping_df)} rows) to: {mapping_csv_path}")

    # 4. Verification Check
    print("[4/4] Verifying generated dataset with Pandas...")
    df = pd.read_csv(clean_csv_path)
    print(f"      Loaded DataFrame Shape: {df.shape}")
    print(f"      Unique Products: {df['product_id'].nunique()} ({df['product_name'].unique().tolist()})")
    print(f"      Unique Platforms: {df['platform'].nunique()} ({df['platform'].unique().tolist()})")
    print(f"      Date Range: {df['recorded_at'].min()} to {df['recorded_at'].max()}")
    print(f"      Unavailable Rows count: {(df['available'] == False).sum()}")
    print("Historical dataset preparation successfully complete!")


if __name__ == "__main__":
    main()
