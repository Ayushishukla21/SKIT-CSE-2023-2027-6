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


def validate_dataset():
    file_path = "data/processed/historical_prices_clean.csv"

    df = pd.read_csv(file_path)

    errors = []

    # Required columns
    missing_columns = [
        col for col in REQUIRED_COLUMNS if col not in df.columns
    ]

    if missing_columns:
        errors.append(f"Missing columns: {missing_columns}")

    # Required identifiers
    if df["product_id"].isna().any():
        errors.append("Missing product IDs")

    if df["platform_id"].isna().any():
        errors.append("Missing platform IDs")

    # Price validation
    invalid_prices = df[
        df["available"] == True
    ]["price"].dropna()

    if (invalid_prices < 0).any():
        errors.append("Negative prices found")

    # Unavailable products must not have price
    unavailable_with_price = df[
        (df["available"] == False) &
        (df["price"].notna())
    ]

    if len(unavailable_with_price) > 0:
        errors.append("Unavailable products have numeric prices")

    # Timestamp validation
    timestamps = pd.to_datetime(
        df["recorded_at"],
        errors="coerce",
        utc=True
    )

    if timestamps.isna().any():
        errors.append("Invalid timestamps found")

    # Duplicate validation
    duplicate_count = df.duplicated(
        subset=["product_id", "platform_id", "recorded_at"]
    ).sum()

    if duplicate_count > 0:
        errors.append(
            f"Duplicate observations found: {duplicate_count}"
        )

    # Platform validation
    valid_platforms = {1, 2, 3, 4}

    if not set(df["platform_id"].dropna().unique()).issubset(
        valid_platforms
    ):
        errors.append("Invalid platform IDs found")

    # Sorting check
    sorted_df = df.sort_values(
        ["product_id", "platform_id", "recorded_at"]
    ).reset_index(drop=True)

    if not df.reset_index(drop=True).equals(sorted_df):
        errors.append("Dataset is not sorted correctly")

    print("\n===== DATASET VALIDATION =====")
    print(f"Rows: {len(df)}")
    print(f"Products: {df['product_id'].nunique()}")
    print(f"Platforms: {df['platform_id'].nunique()}")
    print(
        f"Date range: {df['recorded_at'].min()} "
        f"to {df['recorded_at'].max()}"
    )
    print(f"Missing values: {df[REQUIRED_COLUMNS].isna().sum().sum()}")
    print(f"Duplicate rows: {duplicate_count}")
    print(f"Invalid prices: {(df['price'].dropna() < 0).sum()}")

    if errors:
        print("\nValidation status: FAIL")
        for error in errors:
            print(f"- {error}")
    else:
        print("\nValidation status: PASS")


if __name__ == "__main__":
    validate_dataset()