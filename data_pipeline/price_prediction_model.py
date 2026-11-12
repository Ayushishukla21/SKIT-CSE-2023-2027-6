"""Price Prediction Machine Learning Model for SmartCart AI.

Role: Ayushi Shukla (23ESKCS039) - AI Lead, ML Prediction
Sprint: Sprint 4 - ML Price Prediction

This module implements:
1. Feature preparation and validation (ensuring zero target leakage).
2. Chronological train/test split preventing lookahead bias.
3. Multi-model regression development & comparison:
   - Linear Regression
   - Decision Tree Regressor
   - Random Forest Regressor
4. Comprehensive model evaluation (MAE, MSE, RMSE, R²).
5. Model serialization (joblib) and metadata export (JSON).
6. SmartCartPricePredictor class providing 7-day and 30-day forecasts,
   compatible with smartcart-backend/backend/app/services/prediction_service.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeRegressor

logger = logging.getLogger(__name__)

# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
FEATURES_FILE = PROCESSED_DIR / "price_prediction_features.csv"
FALLBACK_CLEAN_FILE = PROCESSED_DIR / "historical_prices_clean.csv"
MODELS_DIR = BASE_DIR / "models"
MODEL_PATH = MODELS_DIR / "price_prediction_model.pkl"
METADATA_PATH = MODELS_DIR / "model_metadata.json"

# Canonical product package quantities (used when forecasting)
PRODUCT_QUANTITIES: Dict[int, float] = {
    1: 1.0,    # Amul Taaza Milk (1 L)
    2: 5.0,    # Aashirvaad Atta (5 kg)
    3: 1.0,    # Tata Salt (1 kg)
    4: 250.0,  # Tata Tea (250 g)
    5: 70.0,   # Maggi 2-Minute Noodles (70 g)
    6: 250.0,  # Parle-G Biscuits (250 g)
}

FEATURE_COLS = ["product_id", "platform_id", "quantity", "day_of_week", "month"]
TARGET_COL = "target_price"


def load_and_prepare_dataset(
    file_path: Optional[Path] = None,
) -> pd.DataFrame:
    """Load dataset, validate columns, and ensure no arbitrary zeros for missing prices."""
    path = file_path or FEATURES_FILE
    if not path.exists():
        if FALLBACK_CLEAN_FILE.exists():
            path = FALLBACK_CLEAN_FILE
        else:
            raise FileNotFoundError(f"Feature dataset not found at {path}")

    df = pd.read_csv(path)

    # Ensure required target exists
    if TARGET_COL not in df.columns:
        if "price" in df.columns:
            df[TARGET_COL] = df["price"]
        else:
            raise ValueError(f"Neither '{TARGET_COL}' nor 'price' found in dataset")

    # Filter out unavailable products and missing prices
    if "available" in df.columns:
        avail_mask = df["available"].astype(str).str.lower().isin(["true", "1", "yes"])
        df = df[avail_mask].copy()

    df = df.dropna(subset=["product_id", "platform_id", "recorded_at", TARGET_COL])
    df = df[df[TARGET_COL] > 0].copy()

    # Parse timestamps
    df["recorded_at_dt"] = pd.to_datetime(df["recorded_at"], errors="coerce", utc=True)
    df = df.dropna(subset=["recorded_at_dt"])

    # Ensure calendar features exist
    if "day_of_week" not in df.columns:
        df["day_of_week"] = df["recorded_at_dt"].dt.dayofweek
    if "month" not in df.columns:
        df["month"] = df["recorded_at_dt"].dt.month
    if "quantity" not in df.columns:
        df["quantity"] = df["product_id"].map(lambda pid: PRODUCT_QUANTITIES.get(int(pid), 1.0))

    return df


def split_chronologically(
    df: pd.DataFrame,
    test_ratio: float = 0.33,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split dataset chronologically based on recorded timestamps to prevent data leakage."""
    sorted_df = df.sort_values("recorded_at_dt").reset_index(drop=True)
    unique_dates = sorted_df["recorded_at_dt"].dt.date.unique()

    if len(unique_dates) < 2:
        # Fallback to index-based chronological split if single date
        split_idx = int(len(sorted_df) * (1.0 - test_ratio))
        train_df = sorted_df.iloc[:split_idx].copy()
        test_df = sorted_df.iloc[split_idx:].copy()
    else:
        split_date_idx = max(1, int(len(unique_dates) * (1.0 - test_ratio)))
        train_cutoff = unique_dates[split_date_idx - 1]
        train_df = sorted_df[sorted_df["recorded_at_dt"].dt.date <= train_cutoff].copy()
        test_df = sorted_df[sorted_df["recorded_at_dt"].dt.date > train_cutoff].copy()

    # Safety assertion: zero lookahead bias
    if not train_df.empty and not test_df.empty:
        assert train_df["recorded_at_dt"].max() <= test_df["recorded_at_dt"].min(), (
            "Chronological split failed: train timestamps overlap or exceed test timestamps!"
        )

    return train_df, test_df


def build_preprocessor() -> ColumnTransformer:
    """Construct Scikit-learn preprocessor with OneHotEncoder for categoricals."""
    categorical_features = ["product_id", "platform_id"]
    numeric_features = ["quantity", "day_of_week", "month"]

    return ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical_features,
            ),
            ("num", "passthrough", numeric_features),
        ]
    )


def train_and_compare_models(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> Tuple[Dict[str, Dict[str, float]], str, Pipeline]:
    """Train Linear Regression, Decision Tree, and Random Forest and evaluate holdout metrics."""
    X_train = train_df[FEATURE_COLS]
    y_train = train_df[TARGET_COL]

    X_test = test_df[FEATURE_COLS]
    y_test = test_df[TARGET_COL]

    # Verify target leakage prevention
    assert TARGET_COL not in X_train.columns
    assert "price" not in X_train.columns

    candidate_algorithms: Dict[str, Any] = {
        "Linear Regression": LinearRegression(),
        "Decision Tree": DecisionTreeRegressor(max_depth=4, random_state=42),
        "Random Forest": RandomForestRegressor(
            n_estimators=50, max_depth=4, random_state=42
        ),
    }

    metrics_results: Dict[str, Dict[str, float]] = {}
    fitted_pipelines: Dict[str, Pipeline] = {}

    for name, model in candidate_algorithms.items():
        pipeline = Pipeline([
            ("preprocessor", build_preprocessor()),
            ("regressor", model),
        ])
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        mae = float(mean_absolute_error(y_test, y_pred))
        mse = float(mean_squared_error(y_test, y_pred))
        rmse = float(np.sqrt(mse))
        r2 = float(r2_score(y_test, y_pred))

        metrics_results[name] = {
            "mae": round(mae, 4),
            "mse": round(mse, 4),
            "rmse": round(rmse, 4),
            "r2_score": round(r2, 4),
        }
        fitted_pipelines[name] = pipeline

    # Select best model based on lowest MAE on holdout test set
    best_model_name = min(metrics_results.keys(), key=lambda m: metrics_results[m]["mae"])
    best_pipeline = fitted_pipelines[best_model_name]

    return metrics_results, best_model_name, best_pipeline


class SmartCartPricePredictor:
    """Predictor adhering to smartcart-backend/backend/app/services/prediction_service.py.

    Expected signature:
        predict(self, product_id, platform_id, history, days)
    """

    available_periods: Tuple[int, ...] = (7, 30)

    def __init__(
        self,
        model: Optional[Pipeline] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.model = model
        self.metadata = metadata or {}

    @classmethod
    def load(cls, model_path: Optional[Path] = None) -> SmartCartPricePredictor:
        """Load trained model and metadata from disk."""
        m_path = model_path or MODEL_PATH
        meta_path = m_path.parent / "model_metadata.json"

        if not m_path.exists():
            raise FileNotFoundError(f"Trained model not found at {m_path}")

        pipeline = joblib.load(m_path)
        metadata = {}
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load metadata: {e}")

        return cls(model=pipeline, metadata=metadata)

    def save(self, model_path: Optional[Path] = None) -> None:
        """Serialize model to disk."""
        m_path = model_path or MODEL_PATH
        m_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, m_path)

        meta_path = m_path.parent / "model_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

    def predict(
        self,
        product_id: int,
        platform_id: int,
        history: List[Dict[str, Any]],
        days: int = 7,
    ) -> List[Dict[str, Any]]:
        """Generate a forward price prediction for `days` days ahead.

        Parameters
        ----------
        product_id : int
            Product ID in {1..6}.
        platform_id : int
            Platform ID in {1..4}.
        history : list of dict
            List of price observations with 'recorded_at' and 'price', oldest first.
        days : int
            Horizon in available_periods (7 or 30).

        Returns
        -------
        list of dict
            [{"date": "YYYY-MM-DD", "days_ahead": k, "predicted_price": float}, ...]
        """
        if days not in self.available_periods:
            raise ValueError(
                f"days must be one of: {', '.join(str(p) for p in self.available_periods)}"
            )

        if product_id not in (1, 2, 3, 4, 5, 6):
            raise ValueError(f"Unsupported product_id: {product_id}")

        if platform_id not in (1, 2, 3, 4):
            raise ValueError(f"Unsupported platform_id: {platform_id}")

        if not history or len(history) < 2:
            raise ValueError("Insufficient history for prediction (minimum 2 points required)")

        # Validate latest observation has a valid price
        last_obs = history[-1]
        last_price = last_obs.get("price")
        if last_price is None or float(last_price) <= 0:
            raise ValueError("Latest price in history is unavailable or invalid")
        last_price = float(last_price)

        # Parse timestamp of latest observation
        ts_str = str(last_obs.get("recorded_at", "")).strip()
        try:
            if ts_str.endswith("Z"):
                last_dt = datetime.fromisoformat(ts_str[:-1] + "+00:00")
            else:
                last_dt = datetime.fromisoformat(ts_str)
        except Exception:
            last_dt = datetime.now()

        # Compute bounded daily trend from available history points
        first_obs = history[0]
        first_price = float(first_obs.get("price", last_price))
        try:
            first_ts = str(first_obs.get("recorded_at", "")).strip()
            if first_ts.endswith("Z"):
                first_dt = datetime.fromisoformat(first_ts[:-1] + "+00:00")
            else:
                first_dt = datetime.fromisoformat(first_ts)
            elapsed_days = max(1, (last_dt.date() - first_dt.date()).days)
        except Exception:
            elapsed_days = 1

        daily_rate = (last_price - first_price) / elapsed_days
        # Safety bound: cap daily drift at ±0.5% of price to avoid divergence
        max_rate = 0.005 * last_price
        bounded_drift = max(-max_rate, min(max_rate, daily_rate))

        quantity = PRODUCT_QUANTITIES.get(product_id, 1.0)
        predictions = []

        for k in range(1, days + 1):
            future_dt = last_dt + timedelta(days=k)
            date_str = future_dt.strftime("%Y-%m-%d")
            day_of_week = future_dt.weekday()
            month = future_dt.month

            input_features = pd.DataFrame([{
                "product_id": product_id,
                "platform_id": platform_id,
                "quantity": quantity,
                "day_of_week": day_of_week,
                "month": month,
            }])

            # Baseline from trained Scikit-learn model
            if self.model is not None:
                try:
                    model_pred = float(self.model.predict(input_features)[0])
                except Exception as err:
                    logger.debug(f"Model prediction fallback: {err}")
                    model_pred = last_price
            else:
                model_pred = last_price

            # Smooth forecast blending: 70% current price with trend, 30% regressor baseline
            trend_price = last_price + (bounded_drift * k)
            blended_price = (0.7 * trend_price) + (0.3 * model_pred)
            final_price = max(1.0, round(blended_price, 2))

            predictions.append({
                "date": date_str,
                "days_ahead": k,
                "predicted_price": final_price,
            })

        return predictions


def train_and_save_pipeline(
    dataset_path: Optional[Path] = None,
) -> Tuple[SmartCartPricePredictor, Dict[str, Any]]:
    """Execute complete training, evaluation, comparison, and serialization."""
    df = load_and_prepare_dataset(dataset_path)

    # 1. Chronological evaluation
    train_df, test_df = split_chronologically(df, test_ratio=0.33)
    metrics, best_model_name, _ = train_and_compare_models(train_df, test_df)

    # 2. Retrain best model architecture on all available observations
    X_full = df[FEATURE_COLS]
    y_full = df[TARGET_COL]

    candidate_models = {
        "Linear Regression": LinearRegression(),
        "Decision Tree": DecisionTreeRegressor(max_depth=4, random_state=42),
        "Random Forest": RandomForestRegressor(
            n_estimators=50, max_depth=4, random_state=42
        ),
    }

    final_pipeline = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("regressor", candidate_models[best_model_name]),
    ])
    final_pipeline.fit(X_full, y_full)

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_rows": len(df),
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "features": FEATURE_COLS,
        "target": TARGET_COL,
        "models_evaluated": metrics,
        "best_model": best_model_name,
        "available_periods": list(SmartCartPricePredictor.available_periods),
        "limitations": [
            "Trained on historical demo observations",
            "Designed for demonstration of regression price forecasting",
            "Model should be retrained when live ingested feeds are connected",
        ],
    }

    predictor = SmartCartPricePredictor(model=final_pipeline, metadata=metadata)
    predictor.save(MODEL_PATH)

    return predictor, metadata


def main() -> None:
    print("=" * 65)
    print("SmartCart AI: Price Prediction Model Development (Ayushi)")
    print("=" * 65)

    predictor, metadata = train_and_save_pipeline()

    print(f"\nModel training completed successfully!")
    print(f"Total dataset observations: {metadata['dataset_rows']}")
    print(f"Chronological Train rows:   {metadata['train_rows']}")
    print(f"Chronological Test rows:    {metadata['test_rows']}")
    print(f"Features:                   {metadata['features']}")
    print(f"Target:                     {metadata['target']}")

    print("\nModel Evaluation Comparison (Chronological Test Split):")
    print("-" * 65)
    print(f"{'Algorithm':20s} | {'MAE':>8s} | {'MSE':>10s} | {'RMSE':>8s} | {'R2':>8s}")
    print("-" * 65)
    for model_name, scores in metadata["models_evaluated"].items():
        print(
            f"{model_name:20s} | "
            f"{scores['mae']:8.2f} | "
            f"{scores['mse']:10.2f} | "
            f"{scores['rmse']:8.2f} | "
            f"{scores['r2_score']:8.4f}"
        )
    print("-" * 65)
    print(f"Selected Best Model: {metadata['best_model']}")
    print(f"Model saved to:      {MODEL_PATH}")
    print(f"Metadata saved to:   {METADATA_PATH}")

    # Test sample inference for Amul Taaza Milk on Blinkit
    sample_history = [
        {"recorded_at": "2026-09-01T10:00:00Z", "price": 68.0},
        {"recorded_at": "2026-09-05T10:00:00Z", "price": 70.0},
    ]
    preds_7 = predictor.predict(product_id=1, platform_id=1, history=sample_history, days=7)
    print("\nSample 7-Day Forecast (Amul Taaza Milk on Blinkit):")
    for p in preds_7:
        print(f"  Day {p['days_ahead']} ({p['date']}): INR {p['predicted_price']:.2f}")


if __name__ == "__main__":
    main()
