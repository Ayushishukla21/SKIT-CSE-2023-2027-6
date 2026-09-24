
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data_pipeline.validation import (
    validate_products,
    validate_prices,
    validate_offers,
)


class TestValidation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)

        self.products = [
            ["id", "name", "brand", "category", "quantity", "unit", "image_url"],
            ["1", "Amul Taaza Milk", "Amul", "Dairy", "1", "L", ""],
        ]

        self.prices = [
            ["product_id", "platform_id", "price", "currency", "available", "updated_at"],
            ["1", "1", "68.00", "INR", "true", "2026-09-01T10:00:00Z"],
        ]

        self.offers = [
            ["id", "product_id", "platform_id", "title", "description", "discount_amount", "is_active"],
            ["1", "1", "1", "Flat 10 off", "", "10.00", "true"],
        ]

        self.write_csv("products.csv", self.products)
        self.write_csv("prices.csv", self.prices)
        self.write_csv("offers.csv", self.offers)

        self.patcher = patch(
            "data_pipeline.validation.DATA_DIR",
            self.data_dir,
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def write_csv(self, filename, rows):
        with (self.data_dir / filename).open(
            "w", encoding="utf-8", newline=""
        ) as file:
            writer = csv.writer(file)
            writer.writerows(rows)

    def test_valid_products(self):
        product_ids = validate_products()
        self.assertEqual(product_ids, {1})

    def test_duplicate_product_id_fails(self):
        rows = self.products + [
            ["1", "Another Milk", "Amul", "Dairy", "1", "L", ""]
        ]
        self.write_csv("products.csv", rows)

        with self.assertRaisesRegex(ValueError, "duplicate product id"):
            validate_products()

    def test_invalid_product_category_fails(self):
        rows = [
            self.products[0],
            ["1", "Amul Taaza Milk", "Amul", "Unknown", "1", "L", ""],
        ]
        self.write_csv("products.csv", rows)

        with self.assertRaisesRegex(ValueError, "invalid category"):
            validate_products()

    def test_valid_prices(self):
        validate_prices({1})

    def test_unavailable_price_must_be_blank(self):
        rows = [
            self.prices[0],
            ["1", "1", "68.00", "INR", "false", "2026-09-01T10:00:00Z"],
        ]
        self.write_csv("prices.csv", rows)

        with self.assertRaisesRegex(ValueError, "unavailable price must be blank"):
            validate_prices({1})

    def test_price_for_unknown_product_fails(self):
        rows = [
            self.prices[0],
            ["99", "1", "50.00", "INR", "true", "2026-09-01T10:00:00Z"],
        ]
        self.write_csv("prices.csv", rows)

        with self.assertRaisesRegex(ValueError, "product_id does not exist"):
            validate_prices({1})

    def test_valid_offers(self):
        validate_offers({1})

    def test_offer_for_unknown_product_fails(self):
        rows = [
            self.offers[0],
            ["2", "99", "1", "Save 5", "", "5.00", "true"],
        ]
        self.write_csv("offers.csv", rows)

        with self.assertRaisesRegex(ValueError, "product_id does not exist"):
            validate_offers({1})


if __name__ == "__main__":
    unittest.main()