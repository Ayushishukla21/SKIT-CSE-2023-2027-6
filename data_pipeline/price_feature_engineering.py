
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "data" / "processed" / "historical_prices_clean.csv"
OUTPUT_FILE = ROOT / "data" / "processed" / "price_prediction_features.csv"


def prepare_features():
    print("Loading historical price dataset...")

    df = pd.read_csv(INPUT_FILE)

    required = ["product_id", "platform_id", "price", "recorded_at"]
    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df["recorded_at"] = pd.to_datetime(
        df["recorded_at"], errors="coerce", utc=True
    )
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    if "available" in df.columns:
        available = df["available"].astype(str).str.lower().isin(
            ["true", "1", "yes"]
        )
        df = df[available].copy()

    df = df.dropna(
        subset=["product_id", "platform_id", "recorded_at", "price"]
    )
    df = df[df["price"] > 0].copy()

    df = df.sort_values(
        ["product_id", "platform_id", "recorded_at"]
    ).reset_index(drop=True)

    groups = df.groupby(["product_id", "platform_id"], sort=False)

    df["previous_price"] = groups["price"].shift(1)
    df["price_change"] = df["price"] - df["previous_price"]

    df["price_change_percent"] = (
        df["price_change"] / df["previous_price"].replace(0, float("nan"))
    ) * 100

    df["rolling_avg_3"] = groups["price"].transform(
        lambda s: s.shift(1).rolling(3, min_periods=1).mean()
    )

    df["rolling_min_3"] = groups["price"].transform(
        lambda s: s.shift(1).rolling(3, min_periods=1).min()
    )

    df["rolling_max_3"] = groups["price"].transform(
        lambda s: s.shift(1).rolling(3, min_periods=1).max()
    )

    df["day_of_week"] = df["recorded_at"].dt.dayofweek
    df["month"] = df["recorded_at"].dt.month
    df["historical_observation_count"] = groups.cumcount()

    df["target_price"] = df["price"]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print("\nPRICE FEATURE ENGINEERING COMPLETED")
    print("-----------------------------------")
    print("Rows:", len(df))
    print("Products:", df["product_id"].nunique())
    print("Platforms:", df["platform_id"].nunique())
    print("Output:", OUTPUT_FILE)


if __name__ == "__main__":
    prepare_features()
