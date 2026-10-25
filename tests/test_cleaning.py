import unittest

from delta_vault.cleaning import clean_candles, clean_products


class TestCleaning(unittest.TestCase):
    def test_clean_products_removes_duplicate_ids(self):
        products = [
            {"id": 1, "symbol": "BTCUSD"},
            {"id": 1, "symbol": "BTCUSD"},
            {"id": 2, "symbol": "ETHUSD"},
        ]

        df = clean_products(products)

        self.assertEqual(len(df), 2)

    def test_clean_candles_converts_timestamp(self):
        candles = [
            {
                "time": 1792832400,
                "open": 100,
                "high": 110,
                "low": 90,
                "close": 105,
                "volume": 5,
            }
        ]

        df = clean_candles(candles, "BTCUSD")

        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["symbol"], "BTCUSD")
        self.assertTrue(str(df["timestamp"].dtype).startswith("datetime64"))

    def test_empty_candles(self):
        df = clean_candles([], "BTCUSD")

        self.assertTrue(df.empty)
        self.assertIn("timestamp", df.columns)


if __name__ == "__main__":
    unittest.main()