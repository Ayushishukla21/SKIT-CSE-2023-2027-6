import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/processed")

cheapest = pd.read_csv(DATA_DIR / "cheapest_platform_by_product.csv")
changes = pd.read_csv(DATA_DIR / "price_changes.csv")
volatility = pd.read_csv(DATA_DIR / "price_volatility.csv")

# Overall platform statistics
platform_stats = (
    changes.groupby("platform", as_index=False)
    .agg(
        average_price_change=("price_change", "mean"),
        average_price_change_percent=("price_change_percent", "mean"),
        total_price_changes=("price_change", "count")
    )
)

# Product-level price change
product_changes = (
    changes.groupby(["product_id", "product_name"], as_index=False)
    .agg(
        average_price_change=("price_change", "mean"),
        average_price_change_percent=("price_change_percent", "mean"),
        maximum_price_change=("price_change", "max")
    )
)

# Most volatile product/platform combinations
top_volatility = volatility.sort_values(
    "price_range", ascending=False
).head(10)

# Save outputs
platform_stats.to_csv(
    DATA_DIR / "platform_price_change_summary.csv",
    index=False
)

product_changes.to_csv(
    DATA_DIR / "product_price_change_summary.csv",
    index=False
)

top_volatility.to_csv(
    DATA_DIR / "top_price_volatility.csv",
    index=False
)

print("===== PRICE TREND SUMMARY =====")
print(f"Products analysed: {cheapest['product_id'].nunique()}")
print(f"Platforms analysed: {cheapest['platform_id'].nunique()}")

print("\nCheapest platform by product:")
print(
    cheapest[
        ["product_name", "platform", "average_price"]
    ].to_string(index=False)
)

print("\nPlatform price-change summary:")
print(platform_stats.to_string(index=False))

print("\nProduct price-change summary:")
print(product_changes.to_string(index=False))

print("\nTop price volatility:")
print(
    top_volatility[
        ["product_name", "platform", "price_range"]
    ].to_string(index=False)
)

print("\nPrice trend analysis completed successfully.")
