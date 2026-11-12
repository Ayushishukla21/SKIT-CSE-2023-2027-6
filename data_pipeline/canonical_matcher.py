"""Canonical product normalization and cross-platform matching module.

Standardizes product title variations (e.g., "Amul Taaza Milk 1L",
"Amul Taaza Milk - 1 Litre", "Amul Taaza Milk 1 L") and matches them
to canonical grocery products across quick-commerce platforms.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


# Canonical product catalog based on SmartCart AI products.csv
CANONICAL_PRODUCTS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "Amul Taaza Milk",
        "brand": "Amul",
        "category": "Dairy",
        "quantity": 1.0,
        "unit": "L",
        "aliases": [
            "amul taaza milk",
            "amul taaza toned milk",
            "amul taaza fresh toned milk",
            "taaza milk",
        ],
    },
    {
        "id": 2,
        "name": "Aashirvaad Atta",
        "brand": "Aashirvaad",
        "category": "Staples",
        "quantity": 5.0,
        "unit": "kg",
        "aliases": [
            "aashirvaad atta",
            "aashirvaad superior mp atta",
            "aashirvaad shudh chakki atta",
            "aashirvaad whole wheat atta",
        ],
    },
    {
        "id": 3,
        "name": "Tata Salt",
        "brand": "Tata",
        "category": "Staples",
        "quantity": 1.0,
        "unit": "kg",
        "aliases": [
            "tata salt",
            "tata iodized salt",
            "tata vacuum evaporated iodized salt",
            "tata namak",
        ],
    },
    {
        "id": 4,
        "name": "Tata Tea",
        "brand": "Tata",
        "category": "Beverages",
        "quantity": 250.0,
        "unit": "g",
        "aliases": [
            "tata tea",
            "tata tea premium",
            "tata premium tea",
            "tata tea gold",
        ],
    },
    {
        "id": 5,
        "name": "Maggi 2-Minute Noodles",
        "brand": "Maggi",
        "category": "Packaged Food",
        "quantity": 70.0,
        "unit": "g",
        "aliases": [
            "maggi 2-minute noodles",
            "maggi 2 minute noodles",
            "maggi noodles",
            "maggi 2-minute masala noodles",
            "maggi masala 2 minute instant noodles",
        ],
    },
    {
        "id": 6,
        "name": "Parle-G Biscuits",
        "brand": "Parle",
        "category": "Snacks",
        "quantity": 250.0,
        "unit": "g",
        "aliases": [
            "parle-g biscuits",
            "parle-g gluco biscuits",
            "parle g biscuits",
            "parle-g original gluco biscuits",
            "parle g glucose biscuits",
        ],
    },
]

UNIT_SYNONYMS: Dict[str, str] = {
    "l": "L",
    "litre": "L",
    "litres": "L",
    "liter": "L",
    "liters": "L",
    "ltr": "L",
    "ltrs": "L",
    "kg": "kg",
    "kgs": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "g": "g",
    "gm": "g",
    "gms": "g",
    "gram": "g",
    "grams": "g",
    "ml": "ml",
    "mls": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "pcs": "pcs",
    "pc": "pcs",
    "piece": "pcs",
    "pieces": "pcs",
}


def clean_text(text: Optional[str]) -> str:
    """Standardize string by trimming, lowercasing, and normalizing spaces."""
    if text is None:
        return ""
    text = str(text).strip().lower()
    text = re.sub(r"[^\w\s\.\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_pack_size(text: str) -> Tuple[Optional[float], Optional[str]]:
    """Extract numeric quantity and standardized unit from product titles.

    Supports patterns like:
    - '1L', '1 L', '1 Litre', '1.5 Litres'
    - '5kg', '5 kg', '5.0 kgs'
    - '250g', '250 g', '250 gm', '250 grams'
    - '70g', '70 g'
    """
    if not text:
        return None, None

    normalized = text.lower()
    # Match quantity and unit: e.g. 1.5 l, 1L, 500 ml, 5 kg, 250g
    pattern = r"(\d+(?:\.\d+)?)\s*(litres?|liters?|ltrs?|l|kilograms?|kgs?|kg|grams?|gms?|gm|g|millilitres?|milliliters?|mls?|ml|pcs?|pieces?)\b"
    match = re.search(pattern, normalized)

    if match:
        raw_qty = float(match.group(1))
        raw_unit = match.group(2)
        std_unit = UNIT_SYNONYMS.get(raw_unit, raw_unit)
        return raw_qty, std_unit

    return None, None


def normalize_title_for_comparison(title: str) -> str:
    """Remove pack size, punctuation, and filler words to obtain a base title."""
    cleaned = clean_text(title)
    # Remove pack sizes like '1 l', '1 litre', '5 kg', '250 g', '70 g'
    pattern = r"\b\d+(?:\.\d+)?\s*(litres?|liters?|ltrs?|l|kilograms?|kgs?|kg|grams?|gms?|gm|g|millilitres?|milliliters?|mls?|ml|pcs?|pieces?)\b"
    cleaned = re.sub(pattern, "", cleaned)
    # Remove hyphen, extra dots
    cleaned = re.sub(r"[\-\_\.]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def match_product(
    raw_title: str,
    raw_quantity: Optional[Any] = None,
    raw_unit: Optional[Any] = None,
    catalog: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Match a raw product string to a canonical product in the catalog.

    Parameters
    ----------
    raw_title : str
        The raw title string from platforms (e.g. 'Amul Taaza Milk - 1 Litre').
    raw_quantity : Optional[Any]
        Explicit quantity if supplied separately.
    raw_unit : Optional[Any]
        Explicit unit if supplied separately.
    catalog : Optional[List[Dict[str, Any]]]
        Product catalog list; defaults to CANONICAL_PRODUCTS.

    Returns
    -------
    Optional[Dict[str, Any]]
        Matched canonical product details, or None if no match.
    """
    if not raw_title or not str(raw_title).strip():
        return None

    if catalog is None:
        catalog = CANONICAL_PRODUCTS

    # Determine pack size from title if not given
    extracted_qty, extracted_unit = extract_pack_size(raw_title)
    qty = float(raw_quantity) if raw_quantity not in (None, "", "None") else extracted_qty
    unit = UNIT_SYNONYMS.get(str(raw_unit).strip().lower(), str(raw_unit).strip()) if raw_unit not in (None, "", "None") else extracted_unit

    base_title = normalize_title_for_comparison(raw_title)
    raw_lower = clean_text(raw_title)

    best_match = None
    highest_score = 0

    for prod in catalog:
        score = 0
        canonical_name_norm = normalize_title_for_comparison(prod["name"])
        canonical_brand_norm = clean_text(prod["brand"])

        # Check brand match
        if canonical_brand_norm in raw_lower:
            score += 40

        # Check alias matches
        for alias in prod.get("aliases", []):
            alias_norm = normalize_title_for_comparison(alias)
            if alias_norm in base_title or base_title in alias_norm:
                score += 50
                break

        # Check pack size match
        if qty is not None and unit is not None:
            if float(prod["quantity"]) == float(qty) and prod["unit"].lower() == unit.lower():
                score += 30
            else:
                score -= 40  # Mismatched pack size (e.g. 500ml vs 1L)

        if score > highest_score and score >= 70:
            highest_score = score
            best_match = {
                "canonical_product_id": prod["id"],
                "canonical_name": prod["name"],
                "brand": prod["brand"],
                "category": prod["category"],
                "quantity": prod["quantity"],
                "unit": prod["unit"],
                "confidence_score": round(min(score / 120.0, 1.0), 2),
            }

    return best_match


def generate_mapping_dataframe(
    sample_variations: Optional[List[Dict[str, Any]]] = None,
) -> pd.DataFrame:
    """Generate a DataFrame mapping real-world variations to canonical products.

    Creates rows covering variations across Blinkit, Zepto, Instamart,
    and Flipkart Minutes for all canonical items.
    """
    if sample_variations is None:
        sample_variations = [
            # Amul Taaza Milk variations
            {"platform": "Blinkit", "raw_title": "Amul Taaza Milk 1L"},
            {"platform": "Zepto", "raw_title": "Amul Taaza Milk - 1 Litre"},
            {"platform": "Instamart", "raw_title": "Amul Taaza Milk 1 L"},
            {"platform": "Flipkart Minutes", "raw_title": "Amul Taaza Fresh Toned Milk (1 L)"},
            {"platform": "Blinkit", "raw_title": "Amul Taaza Toned Milk Pouch (1 Litre)"},

            # Aashirvaad Atta variations
            {"platform": "Blinkit", "raw_title": "Aashirvaad Atta 5kg"},
            {"platform": "Zepto", "raw_title": "Aashirvaad Superior MP Atta 5 kg"},
            {"platform": "Instamart", "raw_title": "Aashirvaad Whole Wheat Atta 5kg"},
            {"platform": "Flipkart Minutes", "raw_title": "Aashirvaad Shudh Chakki Atta (5 kg)"},

            # Tata Salt variations
            {"platform": "Blinkit", "raw_title": "Tata Salt 1kg"},
            {"platform": "Zepto", "raw_title": "Tata Iodized Salt 1 kg"},
            {"platform": "Instamart", "raw_title": "Tata Salt - 1kg Pouch"},
            {"platform": "Flipkart Minutes", "raw_title": "Tata Vacuum Evaporated Iodized Salt (1 kg)"},

            # Tata Tea variations
            {"platform": "Blinkit", "raw_title": "Tata Tea 250g"},
            {"platform": "Zepto", "raw_title": "Tata Tea Premium 250 g"},
            {"platform": "Instamart", "raw_title": "Tata Premium Tea (250g)"},
            {"platform": "Flipkart Minutes", "raw_title": "Tata Tea Gold Leaf Tea 250 g"},

            # Maggi 2-Minute Noodles variations
            {"platform": "Blinkit", "raw_title": "Maggi 2-Minute Noodles 70g"},
            {"platform": "Zepto", "raw_title": "Maggi 2-Minute Masala Noodles 70 g"},
            {"platform": "Instamart", "raw_title": "Maggi Masala 2 Minute Instant Noodles 70g"},
            {"platform": "Flipkart Minutes", "raw_title": "Maggi 2-Minute Instant Noodles - 70 g"},

            # Parle-G Biscuits variations
            {"platform": "Blinkit", "raw_title": "Parle-G Biscuits 250g"},
            {"platform": "Zepto", "raw_title": "Parle-G Original Gluco Biscuits 250 g"},
            {"platform": "Instamart", "raw_title": "Parle-G Gluco Biscuits - 250g"},
            {"platform": "Flipkart Minutes", "raw_title": "Parle G Glucose Biscuits (250 g)"},
        ]

    rows = []
    for item in sample_variations:
        match = match_product(item["raw_title"])
        if match:
            rows.append({
                "raw_title": item["raw_title"],
                "platform": item["platform"],
                "canonical_product_id": match["canonical_product_id"],
                "canonical_name": match["canonical_name"],
                "brand": match["brand"],
                "category": match["category"],
                "quantity": match["quantity"],
                "unit": match["unit"],
                "match_confidence": match["confidence_score"],
                "match_status": "MATCHED",
            })
        else:
            rows.append({
                "raw_title": item["raw_title"],
                "platform": item["platform"],
                "canonical_product_id": None,
                "canonical_name": None,
                "brand": None,
                "category": None,
                "quantity": None,
                "unit": None,
                "match_confidence": 0.0,
                "match_status": "UNMATCHED",
            })

    return pd.DataFrame(rows)
