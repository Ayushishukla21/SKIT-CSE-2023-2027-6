# SKIT-CSE-2023-2027-6

## Price Data Pipeline

Run the price-processing pipeline from the project root:

    python data_pipeline/price_processing.py

The pipeline reads incoming data from data/raw/raw_prices.csv and creates:

- data/processed/clean_prices.csv - validated and normalized records
- data/processed/rejected_prices.csv - rejected records with reasons

Run the pipeline tests with:

    pytest tests/test_price_processing.py -q
