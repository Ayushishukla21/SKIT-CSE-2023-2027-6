# SmartCart AI – Data Preparation

## 1. Data Source

The dataset is based on the existing SmartCart AI demo data.

The historical price dataset is DEMO / HISTORICAL DEMO DATA.
It is not live scraped marketplace data.

## 2. Dataset Fields

The dataset contains:

- product_id
- product_name
- brand
^))O- category
- platform_id
- platform
- price
- currency
- available
- recorded_at
- quantity
- unit

## 3. Data Cleaning

The cleaning pipeline handles:

- Missing product IDs
- Missing platform IDs
- Invalid prices
- Negative prices
- Duplicate observations
- Unavailable products
- Inconsistent product names
- Inconsistent platform names
- Timestamp normalization
- Dataset sorting

## 4. Missing Values

Unavailable products should have a NULL/NaN price.^X

Unavailable products are not treated as having a price of zero.

## 5. Duplicate Handling

Duplicate observations are checked using:

product_id + platform_id + recorded_at

## 6. Product Normalization

Product names are normalized using a reusable Python function.

This helps identify the same product across different platforms even
when the product name has small formatting differences.

## 7. Platform Normalization

The dataset uses consistent platform IDs:

- 1 = Blinkit
- 2 = Zepto
- 3 = Instamart
- 4 = Flipkart Minutes

## 8. Timestamp Normalization

Timestamps are stored in a consistent ISO-style UTC format.

## 9. ML Readiness

The cleaned dataset provides structured historical price observations
across multiple products, platforms and dates.

It can be used for:

- Historical price analysis
- Product/platform comparison
- Price trend analysis
- Future ML price prediction

## 10. Validation

The final dataset was validated for:

- Required columns
- Missing identifiers
- Invalid prices
- Negative prices
- Duplicate observations
- Unavailable products with prices
- Platform IDs
- Timestamp format
- Dataset sorting

Validation result:

PASS

## 11. Dataset Summary

Rows: 36

Products: 6

Platforms: 4

Date range:
2026-09-01T10:00:00Z to 2026-09-05T10:25:00Z

Missing values: 0

Duplicate rows: 0

Invalid prices: 0

## 12. Limitations

This is demo/historical data and is not live scraped marketplace data.

More historical observations would be required for a production-level
ML price prediction model.

## 13. Price Trend Analysis

The processed historical dataset was further analyzed to identify price
changes, platform-level price movement, and price volatility.

The analysis generates:

- price_platform_summary.csv
- cheapest_platform_by_product.csv
- price_changes.csv
- price_volatility.csv
- platform_price_change_summary.csv
- product_price_change_summary.csv
- top_price_volatility.csv

These outputs support historical price comparison and provide useful
features and observations for the future ML price prediction stage.

The current dataset is demo/historical data and is not live scraped data.

## 14. Price Prediction Model Development (Sprint 4)

### Purpose
Develop a regression-based machine learning model to forecast future grocery product prices across quick-commerce platforms for 7-day and 30-day forecast horizons, supporting consumer decision-making.

### Feature Selection & Data Leakage Prevention
- **Input Features ($X$):**
  - Categorical: `product_id` (1..6), `platform_id` (1..4) encoded via Scikit-learn `OneHotEncoder(handle_unknown="ignore")`.
  - Numerical: `quantity` (pack size), `day_of_week` (0=Monday..6=Sunday), `month` (1..12).
- **Target Variable ($y$):** `target_price` (actual retail selling price in INR).
- **Leakage Prevention:**
  - `target_price` and current `price` are strictly excluded from input feature matrix $X$.
  - Missing prices and unavailable products are never replaced with arbitrary zero values.

### Chronological Train / Test Split
To reflect real-world time-series forecasting and prevent future-to-past data leakage:
- **Training Set:** Earlier observations from `2026-09-01` (24 rows across all 6 products and 4 platforms).
- **Testing Set:** Later holdout observations from `2026-09-05` (12 rows).
- Maximum train timestamp (`2026-09-01T10:25:00Z`) is strictly prior to minimum test timestamp (`2026-09-05T10:00:00Z`).

### Algorithm Evaluation & Comparison
Three Scikit-learn regression models were evaluated on the holdout test split:

| Algorithm | MAE (INR) | MSE | RMSE (INR) | R² Score |
|---|---|---|---|---|
| **Linear Regression** | 3.08 | 11.13 | 3.34 | 0.9987 |
| **Decision Tree Regressor** (max_depth=4) | **2.99** | 14.19 | 3.77 | 0.9983 |
| **Random Forest Regressor** (n_estimators=50) | 3.38 | 23.28 | 4.83 | 0.9972 |

- **Best Model Selected:** **Decision Tree Regressor** (lowest Mean Absolute Error of ₹2.99).
- After holdout evaluation, the production pipeline fits the selected architecture on all available verified records.

### Model Serialization
- The trained pipeline (preprocessing + regressor) is serialized to:
  `models/price_prediction_model.pkl` using `joblib`.
- Evaluation scores, metadata, features, and training date are stored in:
  `models/model_metadata.json`.

### Prediction Interface & Backend Integration
- Implemented `SmartCartPricePredictor` in `data_pipeline/price_prediction_model.py`.
- Adheres directly to the integration contract defined in `smartcart-backend/backend/app/services/prediction_service.py`:
  - `available_periods = (7, 30)`
  - `predict(product_id, platform_id, history, days)`
  - Outputs structured predictions: `[{"date": "YYYY-MM-DD", "days_ahead": k, "predicted_price": float}]`.
  - Implements smooth trend-blending with bounded drift ($\pm 0.5\%$ daily max) anchored to the latest observed actual price.
  - Safe error handling: raises `ValueError` for invalid IDs or $< 2$ history points, safely returning `PREDICTION_UNAVAILABLE` (404) without fabricating prices.

### How to Run & Retrain
Run from project root:
```bash
python data_pipeline/price_prediction_model.py
```
Run automated test suite:
```bash
pytest tests/test_price_prediction_model.py -v
```

### Limitations
- The model is trained on simulated historical demo data (36 observations).
- The high $R^2$ scores reflect the structured nature of the demo catalog.
- Production deployment will require retraining on multi-month live feeds with weather, demand, and festival variables.

