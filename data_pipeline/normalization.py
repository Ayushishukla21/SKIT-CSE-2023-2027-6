import pandas as pd
import re


def normalize_product_name(name):
    if pd.isna(name):
        return ""

    name = str(name).lower().strip()

    # Standardize common variations
    name = name.replace("litre", "l")
    name = name.replace("liter", "l")

    # Remove extra spaces
    name = re.sub(r"\s+", " ", name)

    # Remove spaces around numbers and units
    name = re.sub(r"(\d+)\s+(l|kg|g|ml)", r"\1\2", name)

    return name


def main():
    input_file = "data/raw/historical_prices_raw.csv"
    output_file = "data/processed/product_mapping.csv"

    df = pd.read_csv(input_file)

    df["normalized_product_name"] = df["product_name"].apply(
        normalize_product_name
    )

    mapping = df[
        ["product_id", "product_name", "normalized_product_name"]
    ].drop_duplicates()

    mapping = mapping.sort_values(["product_id", "normalized_product_name"])

    mapping.to_csv(output_file, index=False)

    print("Product normalization completed.")
    print(f"Output file: {output_file}")
    print(f"Products mapped: {mapping['product_id'].nunique()}")
    print(f"Mappings: {len(mapping)}")


if __name__ == "__main__":
    main()