"""
Loads data/products.csv, data/prices.csv and data/offers.csv into MySQL.

Run this after schema.sql has created the tables:

    python seed.py

Safe to re-run: every row is inserted with ON DUPLICATE KEY UPDATE, so
running it again just refreshes the same rows instead of erroring out.
"""

import csv
import os

from dotenv import load_dotenv

load_dotenv()

from app.db.connection import get_connection  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def _read_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _to_bool(value):
    return str(value).strip().lower() == "true"


def _to_decimal_or_none(value):
    value = (value or "").strip()
    return value if value != "" else None


def _to_mysql_datetime(iso_timestamp):
    # "2026-09-01T10:00:00Z" -> "2026-09-01 10:00:00"
    return iso_timestamp.strip().replace("T", " ").replace("Z", "")


def seed_products(cursor):
    rows = _read_csv("products.csv")
    for row in rows:
        cursor.execute(
            """
            INSERT INTO products (id, name, brand, category, quantity, unit, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                brand = VALUES(brand),
                category = VALUES(category),
                quantity = VALUES(quantity),
                unit = VALUES(unit),
                image_url = VALUES(image_url)
            """,
            (
                int(row["id"]),
                row["name"],
                row["brand"],
                row["category"],
                row["quantity"],
                row["unit"],
                row["image_url"] or None,
            ),
        )
    print(f"Seeded {len(rows)} products")


def seed_prices(cursor):
    rows = _read_csv("prices.csv")
    for row in rows:
        cursor.execute(
            """
            INSERT INTO prices (product_id, platform_id, price, currency, available, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                price = VALUES(price),
                currency = VALUES(currency),
                available = VALUES(available),
                updated_at = VALUES(updated_at)
            """,
            (
                int(row["product_id"]),
                int(row["platform_id"]),
                _to_decimal_or_none(row["price"]),
                row["currency"],
                _to_bool(row["available"]),
                _to_mysql_datetime(row["updated_at"]),
            ),
        )
    print(f"Seeded {len(rows)} price rows")


def seed_offers(cursor):
    rows = _read_csv("offers.csv")
    for row in rows:
        cursor.execute(
            """
            INSERT INTO offers (id, product_id, platform_id, title, description, discount_amount, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                product_id = VALUES(product_id),
                platform_id = VALUES(platform_id),
                title = VALUES(title),
                description = VALUES(description),
                discount_amount = VALUES(discount_amount),
                is_active = VALUES(is_active)
            """,
            (
                int(row["id"]),
                int(row["product_id"]),
                int(row["platform_id"]),
                row["title"],
                row["description"] or None,
                _to_decimal_or_none(row["discount_amount"]),
                _to_bool(row["is_active"]),
            ),
        )
    print(f"Seeded {len(rows)} offer rows")


def main():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        seed_products(cursor)
        seed_prices(cursor)
        seed_offers(cursor)
        conn.commit()
        cursor.close()
        print("Seed complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
