import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from data_pipeline import preprocessing


class TestPreprocessing(unittest.TestCase):

    def test_preprocessing_creates_processed_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            data_dir = temp_path / "data"
            processed_dir = data_dir / "processed"
            data_dir.mkdir()

            pd.DataFrame([
                {
                    "id": 1,
                    "name": " Amul Taaza Milk ",
                    "brand": " Amul ",
                    "category": " Dairy ",
                    "quantity": 1,
                    "unit": "L",
                    "image_url": "",
                }
            ]).to_csv(data_dir / "products.csv", index=False)

            pd.DataFrame([
                {
                    "product_id": 1,
                    "platform_id": 1,
                    "price": "",
                    "currency": "INR",
                    "available": False,
                    "updated_at": "2026-09-01T10:00:00Z",
                }
            ]).to_csv(data_dir / "prices.csv", index=False)

            pd.DataFrame([
                {
                    "id": 1,
                    "product_id": 1,
                    "platform_id": 1,
                    "title": " Offer ",
                    "description": "",
                    "discount_amount": 10.00,
                    "is_active": True,
                }
            ]).to_csv(data_dir / "offers.csv", index=False)

            with patch.object(preprocessing, "DATA_DIR", data_dir), \
                 patch.object(preprocessing, "PROCESSED_DIR", processed_dir):
                preprocessing.load_and_preprocess()

            self.assertTrue((processed_dir / "processed_products.csv").exists())
            self.assertTrue((processed_dir / "processed_prices.csv").exists())
            self.assertTrue((processed_dir / "processed_offers.csv").exists())

            processed_products = pd.read_csv(
                processed_dir / "processed_products.csv"
            )
            self.assertEqual(
                processed_products.loc[0, "normalized_name"],
                "amul taaza milk",
            )

            processed_prices = pd.read_csv(
                processed_dir / "processed_prices.csv"
            )
            self.assertTrue(pd.isna(processed_prices.loc[0, "price"]))


if __name__ == "__main__":
    unittest.main()