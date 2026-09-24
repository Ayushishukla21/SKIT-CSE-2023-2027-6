
from pathlib import Path

import pandas as pd

from data_pipeline.normalize import normalize_product


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"


def load_and_preprocess():
    """Load, clean, and save processed copies of the CSV datasets."""

    # Load original CSV files. Keep the originals unchanged.
    products = pd.read_csv(DATA_DIR / "products.csv")
    prices = pd.read_csv(DATA_DIR / "prices.csv")
    offers = pd.read_csv(DATA_DIR / "offers.csv")

    # Clean whitespace in text columns.
    for column in ["name", "brand", "category", "quantity", "unit"]:
        products[column] = products[column].astype("string").str.strip()

    for column in ["currency"]:
        prices[column] = prices[column].astype("string").str.strip()

    for column in ["title", "description"]:
        offers[column] = offers[column].astype("string").str.strip()

    # Add normalized fields for product matching.
    normalized_fields = products.apply(
        lambda row: normalize_product(row.to_dict()),
        axis=1,
        result_type="expand",
    )

    products = pd.concat([products, normalized_fields], axis=1)

    # Keep unavailable prices as missing values, not zero.
    prices["price"] = pd.to_numeric(prices["price"], errors="coerce")

    # Create a separate output folder and save processed copies.
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    products.to_csv(PROCESSED_DIR / "processed_products.csv", index=False)
    prices.to_csv(PROCESSED_DIR / "processed_prices.csv", index=False)
    offers.to_csv(PROCESSED_DIR / "processed_offers.csv", index=False)

    print("Preprocessing complete!")
    print(f"Processed files saved in: {PROCESSED_DIR}")


if __name__ == "__main__":
    load_and_preprocess()