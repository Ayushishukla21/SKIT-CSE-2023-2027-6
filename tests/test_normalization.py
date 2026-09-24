
import unittest

from data_pipeline.normalize import normalize_text, normalize_product


class TestNormalization(unittest.TestCase):

    def test_normalize_text_lowercases_and_strips(self):
        self.assertEqual(
            normalize_text("  AMUL Taaza Milk  "),
            "amul taaza milk",
        )

    def test_normalize_text_collapses_spaces(self):
        self.assertEqual(
            normalize_text("Amul   Taaza    Milk"),
            "amul taaza milk",
        )

    def test_normalize_none_returns_empty_string(self):
        self.assertEqual(normalize_text(None), "")

    def test_normalize_product_fields(self):
        product = {
            "name": "  Amul Taaza Milk ",
            "brand": " AMUL ",
            "quantity": "1",
            "unit": "L",
        }

        result = normalize_product(product)

        self.assertEqual(result["normalized_name"], "amul taaza milk")
        self.assertEqual(result["normalized_brand"], "amul")
        self.assertEqual(result["normalized_quantity"], "1")
        self.assertEqual(result["normalized_unit"], "l")

    def test_normalization_does_not_change_original(self):
        product = {
            "name": "  Amul Taaza Milk ",
            "brand": " AMUL ",
            "quantity": "1",
            "unit": "L",
        }

        original_name = product["name"]
        normalize_product(product)

        self.assertEqual(product["name"], original_name)


if __name__ == "__main__":
    unittest.main()