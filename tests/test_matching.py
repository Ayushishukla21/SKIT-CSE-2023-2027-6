
import unittest

from data_pipeline.matching import products_match


class TestProductMatching(unittest.TestCase):

    def setUp(self):
        self.product_a = {
            "name": "Amul Taaza Milk",
            "brand": "Amul",
            "quantity": "1",
            "unit": "L",
        }

    def test_matching_products_return_true(self):
        product_b = {
            "name": "  AMUL TAAZA MILK ",
            "brand": " AMUL ",
            "quantity": "1",
            "unit": "L",
        }

        self.assertTrue(products_match(self.product_a, product_b))

    def test_different_brand_returns_false(self):
        product_b = {
            "name": "Amul Taaza Milk",
            "brand": "Mother Dairy",
            "quantity": "1",
            "unit": "L",
        }

        self.assertFalse(products_match(self.product_a, product_b))

    def test_different_name_returns_false(self):
        product_b = {
            "name": "Amul Gold Milk",
            "brand": "Amul",
            "quantity": "1",
            "unit": "L",
        }

        self.assertFalse(products_match(self.product_a, product_b))

    def test_different_quantity_returns_false(self):
        product_b = {
            "name": "Amul Taaza Milk",
            "brand": "Amul",
            "quantity": "500",
            "unit": "ml",
        }

        self.assertFalse(products_match(self.product_a, product_b))

    def test_different_unit_returns_false(self):
        product_b = {
            "name": "Amul Taaza Milk",
            "brand": "Amul",
            "quantity": "1",
            "unit": "kg",
        }

        self.assertFalse(products_match(self.product_a, product_b))


if __name__ == "__main__":
    unittest.main()