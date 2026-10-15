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
- category
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

Unavailable products should have a NULL/NaN price.

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