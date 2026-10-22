import pandas as pd
from pathlib import Path

INPUT_FILE = Path("data/processed/historical_prices_clean.csv")
OUTPUT_FILE = Path("data/processed/ml_ready_prices.csv")

df = pd.read_csv(INPUT_FILE)

df["recorded_at"] = pd.to_datetime(df["recorded_at"], utc=True)

df["year"] = df["recorded_at"].dt.year
df["month"] = df["recorded_at"].dt.month
df["day"] = df["recorded_at"].dt.day
df["day_of_week"] = df["recorded_at"].dt.dayofweek

df = df.sort_values(
    ["product_id", "platform_id", "recorded_at"]
).reset_index(drop=True)

df.to_csv(OUTPUT_FILE, index=False)

print("ML-ready dataset created successfully!")
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")
print(f"Saved to: {OUTPUT_FILE}")
