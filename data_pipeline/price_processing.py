import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


PLATFORM_MAP = {
    "blinkit": 1,
    "zepto": 2,
    "instamart": 3,
    "flipkart minutes": 4,
}


def normalize_product_name(value):
    """Normalize product names for consistent matching."""
    if value is None:
        return ""

    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)

    return text


def normalize_platform(value):
    """Convert platform names to the existing platform IDs."""
    if value is None:
        return None

    platform = str(value).strip().lower()
    return PLATFORM_MAP.get(platform)


def normalize_price(value):
    """Convert valid price values such as ₹68 or 68.00 to a number."""
    if value is None:
        return None

    text = str(value).strip()

    if text.startswith("₹"):
        text = text[1:].strip()

    try:
        price = Decimal(text)

        if not price.is_finite() or price < 0:
            return None

        return float(price)

    except (InvalidOperation, ValueError):
        return None


def normalize_availability(value):
    """Convert common availability values to True or False."""
    if isinstance(value, bool):
        return value

    if value is None:
        return None

    value = str(value).strip().lower()

    if value == "true":
        return True

    if value == "false":
        return False

    return None


def normalize_timestamp(value):
    """Normalize a timestamp to UTC ISO-8601 format."""
    if value is None:
        return None

    text = str(value).strip()

    try:
        if text.endswith("Z"):
            timestamp = datetime.fromisoformat(
                text[:-1] + "+00:00"
            )
        else:
            timestamp = datetime.fromisoformat(text)

        if timestamp.tzinfo is None:
            return None

        timestamp = timestamp.astimezone(timezone.utc)

        return timestamp.isoformat().replace("+00:00", "Z")

    except ValueError:
        return None


def normalize_quantity(value):
    """Normalize product quantity to a positive number."""
    if value is None:
        return None

    try:
        quantity = Decimal(str(value).strip())

        if not quantity.is_finite() or quantity <= 0:
            return None

        return float(quantity)

    except (InvalidOperation, ValueError):
        return None


def normalize_unit(value):
    """Normalize quantity units consistently."""
    if value is None:
        return None

    unit = str(value).strip().lower()

    unit_map = {
        "g": "g",
        "gram": "g",
        "grams": "g",
        "kg": "kg",
        "kilogram": "kg",
        "kilograms": "kg",
        "ml": "ml",
        "millilitre": "ml",
        "millilitres": "ml",
        "milliliter": "ml",
        "milliliters": "ml",
        "l": "L",
        "litre": "L",
        "litres": "L",
        "liter": "L",
        "liters": "L",
        "pcs": "pcs",
        "piece": "pcs",
        "pieces": "pcs",
    }

    return unit_map.get(unit)


REQUIRED_FIELDS = {
    "product_id",
    "platform",
    "product_name",
    "available",
    "quantity",
    "unit",
    "timestamp",
}


def validate_price_record(record, valid_product_ids):
    """Validate one incoming price record and return an error message if invalid."""

    missing_fields = [
        field for field in REQUIRED_FIELDS
        if field not in record or record[field] is None
        or str(record[field]).strip() == ""
    ]

    if missing_fields:
        return f"Missing required field(s): {', '.join(sorted(missing_fields))}"

    try:
        product_id = int(str(record["product_id"]).strip())
    except (ValueError, TypeError):
        return "Invalid product_id"

    if product_id not in valid_product_ids:
        return "Invalid product_id"

    platform_id = normalize_platform(record["platform"])

    if platform_id is None:
        return "Invalid platform"

    available = normalize_availability(record["available"])

    if available is None:
        return "Invalid availability"

    price = normalize_price(record["price"])

    if available and price is None:
        return "Valid price is required when product is available"

    if not available:
        if str(record["price"]).strip() not in {"", "None", "none"}:
            return "Unavailable product must have no price"

    quantity = normalize_quantity(record["quantity"])

    if quantity is None:
        return "Invalid quantity"

    unit = normalize_unit(record["unit"])

    if unit is None:
        return "Invalid unit"

    timestamp = normalize_timestamp(record["timestamp"])

    if timestamp is None:
        return "Invalid timestamp"

    return None


def detect_duplicates(records):
    """Find duplicate records using product, platform, and timestamp."""

    seen = set()
    duplicates = []

    for index, record in enumerate(records, start=1):
        key = (
            str(record.get("product_id", "")).strip(),
            normalize_platform(record.get("platform")),
            str(record.get("timestamp", "")).strip(),
        )

        if key in seen:
            duplicates.append(index)
        else:
            seen.add(key)

    return duplicates


def process_price_data(records, valid_product_ids):
    """Clean, validate, normalize, and separate incoming price records."""

    clean_records = []
    rejected_records = []

    duplicate_indexes = set(detect_duplicates(records))

    for index, record in enumerate(records, start=1):

        if index in duplicate_indexes:
            rejected_records.append({
                "row": index,
                "reason": "Duplicate record",
                "record": record,
            })
            continue

        error = validate_price_record(record, valid_product_ids)

        if error:
            rejected_records.append({
                "row": index,
                "reason": error,
                "record": record,
            })
            continue

        product_id = int(str(record["product_id"]).strip())
        platform_id = normalize_platform(record["platform"])
        available = normalize_availability(record["available"])
        price = normalize_price(record["price"])

        if not available:
            price = None

        clean_records.append({
            "product_id": product_id,
            "platform_id": platform_id,
            "price": price,
            "currency": "INR",
            "available": available,
            "updated_at": normalize_timestamp(record["timestamp"]),
        })

    return clean_records, rejected_records


if __name__ == "__main__":
    import csv
    from pathlib import Path

    base_dir = Path(__file__).resolve().parent.parent
    raw_file = base_dir / "data" / "raw" / "raw_prices.csv"
    output_dir = base_dir / "data" / "processed"
    clean_file = output_dir / "clean_prices.csv"
    rejected_file = output_dir / "rejected_prices.csv"

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(raw_file, "r", encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    with open(base_dir / "data" / "products.csv", "r", encoding="utf-8", newline="") as file:
        product_rows = csv.DictReader(file)
        valid_product_ids = {
            int(row["id"])
            for row in product_rows
        }

    clean_records, rejected_records = process_price_data(
        records,
        valid_product_ids,
    )

    clean_headers = [
        "product_id",
        "platform_id",
        "price",
        "currency",
        "available",
        "updated_at",
    ]

    with open(clean_file, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=clean_headers)
        writer.writeheader()
        writer.writerows(clean_records)

    rejected_headers = ["row", "reason", "record"]

    with open(rejected_file, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rejected_headers)
        writer.writeheader()

        for item in rejected_records:
            writer.writerow({
                "row": item["row"],
                "reason": item["reason"],
                "record": str(item["record"]),
            })

    print(f"Clean records: {len(clean_records)}")
    print(f"Rejected records: {len(rejected_records)}")
    print(f"Clean output: {clean_file}")
    print(f"Rejected output: {rejected_file}")

