# SmartCart AI – Data Directory Structure & Documentation

**Role:** Ayushi (Dataset Engineering, Data Cleaning, Normalization, Product Matching, ML Readiness)  
**Project:** SmartCart AI – Intelligent Grocery Price Monitoring and Recommendation Platform  
**Sprint:** Sprint 3 / October Week 2 Final

---

## 1. Directory Structure

```text
data/
├── README.md                              # This documentation file
├── offers.csv                             # Seed promotional offers
├── prices.csv                             # Baseline snapshot prices across platforms
├── products.csv                           # Canonical product catalog (6 core grocery items)
├── raw/
│   ├── historical_prices_raw.csv          # Raw historical observations (with simulated real-world noise)
│   └── raw_prices.csv                     # Single-batch ingestion sample
└── processed/
    ├── historical_prices_clean.csv        # Cleaned, normalized, ML-ready historical price dataset
    ├── ml_ready_prices.csv                # Feature-engineered dataset with lag prices and changes
    ├── product_mapping.csv                # Cross-platform raw title to canonical product mapping
    ├── dataset_coverage_summary.csv       # Audit matrix of observations and coverage status per combination
    ├── price_analysis_summary.csv         # Summary statistics, price volatility, and cheapest platforms
    ├── historical_rejected_records.csv    # Audit log of rejected/invalid raw records with reasons
    ├── clean_prices.csv                   # Validated batch price records
    ├── processed_offers.csv               # Preprocessed active offers
    ├── processed_prices.csv               # Preprocessed snapshot prices
    └── processed_products.csv             # Preprocessed canonical products with normalized fields
```

---

## 2. Key Dataset Files

### `data/processed/historical_prices_clean.csv`
- **Purpose:** Primary historical price dataset for price trend monitoring, cross-platform price comparison, and ML feature extraction.
- **Row count:** 960 rows.
- **Date range:** `2026-09-01T10:00:00Z` to `2026-10-10T10:00:00Z` (40 consecutive days).
- **Products:** 6 canonical grocery items.
- **Platforms:** 4 quick-commerce platforms (Blinkit, Zepto, Instamart, Flipkart Minutes).
- **Format:** UTF-8 CSV, strict ISO 8601 UTC timestamps, sorted hierarchically by `(product_id, platform_id, recorded_at)`.
- **Unavailable Rule:** Unavailable products (`available = false`) strictly have blank/NaN prices (never ₹0).

---

### `data/processed/ml_ready_prices.csv`
- **Purpose:** ML-ready dataset enriched with backward-looking time-series features.
- **Row count:** 960 rows (20 columns).
- **Key Features:**
  - `prev_price`: Immediately preceding valid observed price within the same `(product_id, platform_id)` series.
  - `prev_recorded_at`: Timestamp of the preceding observation.
  - `price_change`: Absolute change in price (`price - prev_price`).
  - `price_change_pct`: Percentage change in price (`(price - prev_price) / prev_price * 100`).
  - `day_of_week`: Integer representing day of week (0 = Monday, 6 = Sunday).
  - `month`: Integer calendar month (1 to 12).
- **Data Leakage Guarantee:** Strictly historical, zero lookahead bias, first row of each combination starts with `NaN` previous prices.

---

### `data/processed/dataset_coverage_summary.csv`
- **Purpose:** Audit matrix verifying observation counts, availability rate, and temporal continuity across all 24 `(product_id, platform_id)` combinations.
- **Summary:** 23 combinations have complete 100% or >95% coverage; 1 combination (Tata Tea on Flipkart Minutes) is properly flagged as `INSUFFICIENT_OBSERVATIONS (100% Unavailable)`.

---

### `data/processed/price_analysis_summary.csv`
- **Purpose:** Statistical breakdown per combination including `min_price`, `max_price`, `mean_price`, `price_volatility_std`, `volatility_cv_pct`, and `cheapest_platform_for_product`.

---

### `data/processed/product_mapping.csv`
- **Purpose:** Cross-platform matching lookup table. Maps raw product title variants observed on Blinkit, Zepto, Instamart, and Flipkart Minutes (e.g. `"Amul Taaza Milk - 1 Litre"`) to canonical products.

---

### `data/raw/historical_prices_raw.csv`
- **Purpose:** Represents incoming uncleaned ingestion records with simulated real-world platform variations (casing inconsistencies, raw titles, currency symbols, and deliberate dirty test cases).

---

## 3. How to Run Data Engineering Pipelines

### 1. Regenerate Historical Dataset & Canonical Mapping
```bash
python data_pipeline/prepare_historical_data.py
```

### 2. Run Dataset Coverage Audit
```bash
python data_pipeline/coverage_audit.py
```

### 3. Generate ML Features (`ml_ready_prices.csv`)
```bash
python data_pipeline/feature_engineering.py
```

### 4. Run Price & Volatility Analysis
```bash
python data_pipeline/price_analysis.py
```

### 5. Validate Datasets
```bash
python validate_dataset.py data/processed/historical_prices_clean.csv
python validate_dataset.py data/processed/ml_ready_prices.csv
```

### 6. Run Complete Test Suite
```bash
pytest tests/ -v
```
