"""Unit tests for product normalization and canonical matching across platforms."""

import unittest
from data_pipeline.canonical_matcher import (
    clean_text,
    extract_pack_size,
    match_product,
    normalize_title_for_comparison,
    generate_mapping_dataframe,
)


class TestCanonicalMatcher(unittest.TestCase):

    def test_clean_text(self):
        self.assertEqual(clean_text("  Amul  Taaza - Milk "), "amul taaza - milk")
        self.assertEqual(clean_text(None), "")

    def test_extract_pack_size_litres(self):
        qty, unit = extract_pack_size("Amul Taaza Milk 1L")
        self.assertEqual((qty, unit), (1.0, "L"))

        qty, unit = extract_pack_size("Amul Taaza Milk - 1 Litre")
        self.assertEqual((qty, unit), (1.0, "L"))

        qty, unit = extract_pack_size("Amul Taaza Milk 1 L")
        self.assertEqual((qty, unit), (1.0, "L"))

    def test_extract_pack_size_kilograms_and_grams(self):
        qty, unit = extract_pack_size("Aashirvaad Atta 5kg")
        self.assertEqual((qty, unit), (5.0, "kg"))

        qty, unit = extract_pack_size("Tata Tea 250g")
        self.assertEqual((qty, unit), (250.0, "g"))

        qty, unit = extract_pack_size("Maggi 2-Minute Noodles 70 g")
        self.assertEqual((qty, unit), (70.0, "g"))

    def test_normalize_title_removes_pack_size(self):
        cleaned = normalize_title_for_comparison("Amul Taaza Milk 1L")
        self.assertNotIn("1l", cleaned)
        self.assertIn("amul taaza milk", cleaned)

    def test_match_milk_variations_to_canonical_product(self):
        variations = [
            "Amul Taaza Milk 1L",
            "Amul Taaza Milk - 1 Litre",
            "Amul Taaza Milk 1 L",
            "Amul Taaza Fresh Toned Milk (1 L)",
        ]
        for title in variations:
            match = match_product(title)
            self.assertIsNotNone(match, f"Failed to match: {title}")
            self.assertEqual(match["canonical_product_id"], 1)
            self.assertEqual(match["canonical_name"], "Amul Taaza Milk")
            self.assertEqual(match["brand"], "Amul")
            self.assertEqual(match["unit"], "L")

    def test_match_atta_variations(self):
        variations = [
            "Aashirvaad Atta 5kg",
            "Aashirvaad Superior MP Atta 5 kg",
            "Aashirvaad Whole Wheat Atta 5kg",
            "Aashirvaad Shudh Chakki Atta (5 kg)",
        ]
        for title in variations:
            match = match_product(title)
            self.assertIsNotNone(match, f"Failed to match: {title}")
            self.assertEqual(match["canonical_product_id"], 2)
            self.assertEqual(match["canonical_name"], "Aashirvaad Atta")
            self.assertEqual(match["brand"], "Aashirvaad")

    def test_match_tata_salt_and_tea(self):
        salt_match = match_product("Tata Salt 1kg")
        self.assertIsNotNone(salt_match)
        self.assertEqual(salt_match["canonical_product_id"], 3)
        self.assertEqual(salt_match["canonical_name"], "Tata Salt")

        tea_match = match_product("Tata Premium Tea (250g)")
        self.assertIsNotNone(tea_match)
        self.assertEqual(tea_match["canonical_product_id"], 4)
        self.assertEqual(tea_match["canonical_name"], "Tata Tea")

    def test_match_maggi_and_parle_g(self):
        maggi_match = match_product("Maggi 2-Minute Masala Noodles 70 g")
        self.assertIsNotNone(maggi_match)
        self.assertEqual(maggi_match["canonical_product_id"], 5)
        self.assertEqual(maggi_match["canonical_name"], "Maggi 2-Minute Noodles")

        parle_match = match_product("Parle-G Original Gluco Biscuits 250 g")
        self.assertIsNotNone(parle_match)
        self.assertEqual(parle_match["canonical_product_id"], 6)
        self.assertEqual(parle_match["canonical_name"], "Parle-G Biscuits")

    def test_unmatched_returns_none(self):
        self.assertIsNone(match_product("Completely Random Smartphone Case"))
        self.assertIsNone(match_product(""))
        self.assertIsNone(match_product(None))

    def test_generate_mapping_dataframe(self):
        df = generate_mapping_dataframe()
        self.assertGreater(len(df), 20)
        self.assertIn("canonical_product_id", df.columns)
        self.assertIn("match_status", df.columns)
        self.assertTrue((df["match_status"] == "MATCHED").all())


if __name__ == "__main__":
    unittest.main()
