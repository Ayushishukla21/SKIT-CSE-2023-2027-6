import csv
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation


# Find the data folder relative to this Python file
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CATEGORIES = {
    "Dairy",
    "Staples",
    "Beverages",
    "Snacks",
    "Packaged Food",
}

UNITS = {"g", "kg", "ml", "L", "pcs"}

PRODUCT_HEADERS = [
    "id", "name", "brand", "category",
    "quantity", "unit", "image_url"
]

PRICE_HEADERS = [
    "product_id", "platform_id", "price",
    "currency", "available", "updated_at"
]

OFFER_HEADERS = [
    "id", "product_id", "platform_id", "title",
    "description", "discount_amount", "is_active"
]


def read_csv(filename, expected_headers):
    path = DATA_DIR / filename

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames != expected_headers:
            raise ValueError(
                f"{filename}: headers do not match the schema"
            )

        return list(reader)


def positive_integer(value, field, row_number):
    try:
        number = int(value)
        if number <= 0:
            raise ValueError
        return number
    except (ValueError, TypeError):
        raise ValueError(
            f"Row {row_number}: {field} must be a positive integer"
        )


def positive_decimal(value, field, row_number):
    try:
        number = Decimal(value)
        if not number.is_finite() or number <= 0:
            raise ValueError
        return number
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(
            f"Row {row_number}: {field} must be greater than zero"
        )


def check_timestamp(value, row_number):
    try:
        if not value.endswith("Z"):
            raise ValueError
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise ValueError(
            f"Row {row_number}: updated_at must be ISO 8601 UTC"
        )


def validate_products():
    rows = read_csv("products.csv", PRODUCT_HEADERS)
    product_ids = set()

    for row_number, row in enumerate(rows, start=2):
        product_id = positive_integer(row["id"], "id", row_number)

        if product_id in product_ids:
            raise ValueError(f"Row {row_number}: duplicate product id")
        product_ids.add(product_id)

        if not row["name"] or len(row["name"]) > 150:
            raise ValueError(f"Row {row_number}: invalid product name")

        if not row["brand"] or len(row["brand"]) > 80:
            raise ValueError(f"Row {row_number}: invalid brand")

        if row["category"] not in CATEGORIES:
            raise ValueError(f"Row {row_number}: invalid category")

        positive_decimal(row["quantity"], "quantity", row_number)

        if row["unit"] not in UNITS:
            raise ValueError(f"Row {row_number}: invalid unit")

    return product_ids


def validate_prices(product_ids):
    rows = read_csv("prices.csv", PRICE_HEADERS)
    seen_pairs = set()

    for row_number, row in enumerate(rows, start=2):
        product_id = positive_integer(
            row["product_id"], "product_id", row_number
        )
        platform_id = positive_integer(
            row["platform_id"], "platform_id", row_number
        )

        if product_id not in product_ids:
            raise ValueError(
                f"Row {row_number}: product_id does not exist"
            )

        if platform_id not in {1, 2, 3, 4}:
            raise ValueError(f"Row {row_number}: invalid platform_id")

        pair = (product_id, platform_id)
        if pair in seen_pairs:
            raise ValueError(f"Row {row_number}: duplicate product/platform")
        seen_pairs.add(pair)

        if row["currency"] != "INR":
            raise ValueError(f"Row {row_number}: currency must be INR")

        if row["available"] not in {"true", "false"}:
            raise ValueError(f"Row {row_number}: invalid available value")

        if row["available"] == "true":
            positive_decimal(row["price"], "price", row_number)
        elif row["price"] != "":
            raise ValueError(
                f"Row {row_number}: unavailable price must be blank"
            )

        check_timestamp(row["updated_at"], row_number)


def validate_offers(product_ids):
    rows = read_csv("offers.csv", OFFER_HEADERS)
    offer_ids = set()
    active_pairs = set()

    for row_number, row in enumerate(rows, start=2):
        offer_id = positive_integer(row["id"], "id", row_number)
        product_id = positive_integer(
            row["product_id"], "product_id", row_number
        )
        platform_id = positive_integer(
            row["platform_id"], "platform_id", row_number
        )

        if offer_id in offer_ids:
            raise ValueError(f"Row {row_number}: duplicate offer id")
        offer_ids.add(offer_id)

        if product_id not in product_ids:
            raise ValueError(
                f"Row {row_number}: product_id does not exist"
            )

        if platform_id not in {1, 2, 3, 4}:
            raise ValueError(f"Row {row_number}: invalid platform_id")

        if not row["title"] or len(row["title"]) > 100:
            raise ValueError(f"Row {row_number}: invalid offer title")

        if row["is_active"] not in {"true", "false"}:
            raise ValueError(f"Row {row_number}: invalid is_active value")

        if row["discount_amount"] != "":
            try:
                amount = Decimal(row["discount_amount"])
                if not amount.is_finite() or amount < 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                raise ValueError(
                    f"Row {row_number}: invalid discount_amount"
                )

        if row["is_active"] == "true":
            pair = (product_id, platform_id)
            if pair in active_pairs:
                raise ValueError(
                    f"Row {row_number}: more than one active offer "
                    "for a product/platform"
                )
            active_pairs.add(pair)


def main():
    try:
        product_ids = validate_products()
        validate_prices(product_ids)
        validate_offers(product_ids)

        print("Validation successful!")
        print("Products, prices, and offers passed the checks.")

    except (ValueError, FileNotFoundError) as error:
        print(f"Validation failed: {error}")


if __name__ == "__main__":
    main()