
import unittest
import pandas as pd


class TestPriceFeatureEngineering(unittest.TestCase):

    def setUp(self):
        self.df = pd.DataFrame({
            "product_id": ["P1", "P1", "P1", "P2", "P2"],
            "platform": ["Blinkit", "Blinkit", "Blinkit", "Zepto", "Zepto"],
            "price": [100, 110, 120, 50, 60]
        })

    def test_previous_price(self):
        self.df["previous_price"] = (
            self.df.groupby(["product_id", "platform"])["price"].shift(1)
        )

        self.assertTrue(pd.isna(self.df.loc[0, "previous_price"]))
        self.assertEqual(self.df.loc[1, "previous_price"], 100)
        self.assertEqual(self.df.loc[2, "previous_price"], 110)

    def test_price_change(self):
        self.df["previous_price"] = (
            self.df.groupby(["product_id", "platform"])["price"].shift(1)
        )
        self.df["price_change"] = (
            self.df["price"] - self.df["previous_price"]
        )

        self.assertEqual(self.df.loc[1, "price_change"], 10)
        self.assertEqual(self.df.loc[2, "price_change"], 10)

    def test_products_are_separate(self):
        self.df["previous_price"] = (
            self.df.groupby(["product_id", "platform"])["price"].shift(1)
        )

        self.assertTrue(pd.isna(self.df.loc[3, "previous_price"]))
        self.assertEqual(self.df.loc[4, "previous_price"], 50)

    def test_percentage_change(self):
        previous_price = 100
        current_price = 110

        change_percent = (
            (current_price - previous_price) / previous_price
        ) * 100

        self.assertEqual(change_percent, 10)


if __name__ == "__main__":
    unittest.main()
