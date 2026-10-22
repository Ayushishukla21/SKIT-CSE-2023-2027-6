import pandas as pd

FILE = "data/processed/ml_ready_prices.csv"

df = pd.read_csv(FILE)

required = [
    "product_id",
    "product_name",
    "platform_id",
    "platform",
    "price",
    "available",
    "recorded_at",
    "quantity",
    "unit"
]

missing_columns = [c for c in required if c not in df.columns]

print("===== ML READINESS CHECK =====")

if missing_columns:
    print("Missing columns:", missing_columns)
    print("Status: FAIL")
    raise SystemExit(1)

df["recorded_at"] = pd.to_datetime(df["recorded_at"], errors="coerce")

invalid_timestamps = df["recorded_at"].isna().sum()
invalid_prices = ((df["price"].notna()) & (df["price"] < 0)).sum()

available_with_missing_price = (
    (df["available"] == True) & df["price"].isna()
).sum()

unavailable_with_price = (
    (df["available"] == False) & df["price"].notna()
).sum()

duplicates = df.duplicated(
    subset=["product_id", "platform_id", "recorded_at"]
).sum()

print("Rows:", len(df))
print("Products:", df["product_id"].nunique())
print("Platforms:", df["platform_id"].nunique())
print("Invalid timestamps:", invalid_timestamps)
print("Invalid prices:", invalid_prices)
print("Available products missing price:", available_with_missing_price)
print("Unavailable products with price:", unavailable_with_price)
print("Duplicate observations:", duplicates)

if any([
    invalid_timestamps,
    invalid_prices,
    available_with_missing_price,
    unavailable_with_price,
    duplicates
]):
    print("ML Readiness: FAIL")
else:
    print("ML Readiness: PASS")
