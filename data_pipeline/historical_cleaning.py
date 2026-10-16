import os
import re
import pandas as pd
import numpy as np


RAW_FILE = "data/raw/historical_prices_raw.csv"
OUTPUT_FILE = "data/processed/historical_prices_clean.csv"


PLATFORM_MAP = {
    "blinkit": (1, "Blinkit"),
    "zepto": (2, "Zepto"),
    "instamart": (3, "Instamart"),
    "flipkart minutes": (4, "Flipkart Minutes"),
    "flipkartminutes": (4, "Flipkart Minutes"),
}


def normalize_product_name(name):
    """Normalize product names for consistent matching."""
    if pd.isna(name):
        return np.nan

    name = str(name).strip().lower()
    name = re.sub(r"\s+", " ", name)

    replacements = {
        "amul taaza milk - 1 litre": "amul taaza milk",
        "amul taaza milk 1l": "amul taaza milk",
        "amul taaza milk 1 l": "amul taaza milk",
        "aashirvaad atta 5 kg": "aashirvaad atta",
        "tata salt 1 kg": "tata salt",
        "tata tea 250 g": "tata tea",
        "maggi 2 minute noodles": "maggi 2-minute noodles",
        "maggi 2-minutes noodles": "maggi 2-minute noodles",
        "parle g biscuits": "parle-g biscuits",
        "parle-g biscuit": "parle-g biscuits",
    }

    return replacements.get(name, name)


def normalize_platform(value):
    """Normalize platform names."""
    if pd.isna(value):
        return np.nan

    key = str(value).strip().lower()
    key = re.sub(r"\s+", " ", key)

    if key not in PLATFORM_MAP:
        return np.nan

    return PLATFORM_MAP[key][1]


def get_platform_id(value):
    """Return the standard platform ID."""
    if pd.isna(value):
        return np.nan

    key = str(value).strip().lower()
    key = re.sub(r"\s+", " ", key)

    if key not in PLATFORM_MAP:
        return np.nan

    return PLATFORM_MAP[key][0]


def clean_price(value):
    """Convert price values such as ₹68.00 or ' 265.00 ' into numbers."""
    if pd.isna(value):
        return np.nan

    value = str(value).strip()

    if value == "":
        return np.nan

    value = value.replace("₹", "")
    value = value.replace(",", "")
    value = value.strip()

    try:
        return float(value)
    except ValueError:
        return np.nan


def normalize_timestamp(value):
    """Convert timestamps to UTC ISO format."""
    parsed = pd.to_datetime(value, errors="coerce", utc=True)

    if pd.isna(parsed):
        return pd.NaT

    return parsed


def main():
    if not os.path.exists(RAW_FILE):
        raise FileNotFoundError(f"Raw dataset not found: {RAW_FILE}")

    df = pd.read_csv(RAW_FILE)

    required_columns = [
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

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # Remove leading/trailing spaces from text fields
    text_columns = [
        "product_name",
        "brand",
        "category",
        "platform",
        "currency",
        "unit",
    ]

    for column in text_columns:
        df[column] = df[column].astype("string").str.strip()

    # Normalize product names
    df["product_name"] = df["product_name"].apply(
        normalize_product_name
    )

    # Normalize platform names and IDs
    df["platform"] = df["platform"].apply(normalize_platform)
    df["platform_id"] = df["platform"].apply(get_platform_id)

    # Clean prices
    df["price"] = df["price"].apply(clean_price)

    # Convert available to boolean
    df["available"] = (
        df["available"]
        .astype("string")
        .str.strip()
        .str.lower()
        .map({
            "true": True,
            "false": False,
            "1": True,
            "0": False,
        })
    )

    # Normalize timestamps
    df["recorded_at"] = df["recorded_at"].apply(
        normalize_timestamp
    )

    # Convert product IDs to numeric
    df["product_id"] = pd.to_numeric(
        df["product_id"],
        errors="coerce"
    )

    # Convert quantity to numeric
    df["quantity"] = pd.to_numeric(
        df["quantity"],
        errors="coerce"
    )

    # Standard currency
    df["currency"] = df["currency"].str.upper()

    # Unavailable products must NOT have price = 0
    df.loc[df["available"] == False, "price"] = np.nan

    # Negative prices are invalid
    df.loc[df["price"] < 0, "price"] = np.nan

    # Remove records with invalid required identifiers
    df = df.dropna(
        subset=[
            "product_id",
            "product_name",
            "platform_id",
            "platform",
            "recorded_at",
        ]
    )

    # Remove invalid timestamps
    df = df.dropna(subset=["recorded_at"])

    # Remove duplicate observations
    df = df.drop_duplicates(
        subset=[
            "product_id",
            "platform_id",
            "recorded_at",
        ],
        keep="first",
    )

    # Sort chronologically by product, platform and date
    df = df.sort_values(
        by=[
            "product_id",
            "platform_id",
            "recorded_at",
        ]
    ).reset_index(drop=True)

    # Convert timestamp to ISO UTC string
    df["recorded_at"] = df["recorded_at"].dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    # Keep only useful ML-ready fields
    final_columns = [
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

    df = df[final_columns]

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("Historical price cleaning completed.")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Rows: {len(df)}")
    print(f"Products: {df['product_id'].nunique()}")
    print(f"Platforms: {df['platform_id'].nunique()}")
    print(
        f"Date range: "
        f"{df['recorded_at'].min()} to "
        f"{df['recorded_at'].max()}"
    )
    print(
        f"Missing prices: "
        f"{df['price'].isna().sum()}"
    )


if __name__ == "__main__":
    main()