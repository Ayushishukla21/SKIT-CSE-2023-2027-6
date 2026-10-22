import pandas as pd
from pathlib import Path

INPUT_FILE = Path("data/processed/historical_prices_clean.csv")
OUTPUT_DIR = Path("data/processed")

df = pd.read_csv(INPUT_FILE)
df["recorded_at"] = pd.to_datetime(df["recorded_at"], utc=True)

# 1. Average price by product and platform
platform_summary = (
    df[df["available"] == True]
    .groupby(["product_id", "product_name", "platform_id", "platform"], as_index=False)
    .agg(
        average_price=("price", "mean"),
        minimum_price=("price", "min"),
        maximum_price=("price", "max"),
        observations=("price", "count")
    )
)

platform_summary.to_csv(
    OUTPUT_DIR / "price_platform_summary.csv",
    index=False
)

# 2. Cheapest platform for each product
cheapest_platform = (
    platform_summary.loc[
        platform_summary.groupby("product_id")["average_price"].idxmin()
    ]
    .sort_values("product_id")
)

cheapest_platform.to_csv(
    OUTPUT_DIR / "cheapest_platform_by_product.csv",
    index=False
)

# 3. Price change over time
df = df.sort_values(["product_id", "platform_id", "recorded_at"])

df["previous_price"] = (
    df.groupby(["product_id", "platform_id"])["price"].shift(1)
)

df["price_change"] = df["price"] - df["previous_price"]

df["price_change_percent"] = (
    df["price_change"] / df["previous_price"] * 100
)

price_changes = df.dropna(subset=["previous_price"])

price_changes.to_csv(
    OUTPUT_DIR / "price_changes.csv",
    index=False
)

# 4. Price volatility
volatility = (
    df[df["available"] == True]
    .groupby(["product_id", "product_name", "platform"], as_index=False)
    .agg(
        average_price=("price", "mean"),
        price_std=("price", "std"),
        minimum_price=("price", "min"),
        maximum_price=("price", "max")
    )
)

volatility["price_range"] = (
    volatility["maximum_price"] - volatility["minimum_price"]
)

volatility.to_csv(
    OUTPUT_DIR / "price_volatility.csv",
    index=False
)

print("===== PRICE ANALYSIS COMPLETE =====")
print(f"Input rows: {len(df)}")
print(f"Products: {df['product_id'].nunique()}")
print(f"Platforms: {df['platform_id'].nunique()}")
print("Created:")
print("- price_platform_summary.csv")
print("- cheapest_platform_by_product.csv")
print("- price_changes.csv")
print("- price_volatility.csv")
