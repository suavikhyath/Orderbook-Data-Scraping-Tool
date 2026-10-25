import unittest
from unittest.mock import Mock, patch

from delta_vault import DeltaClient


class TestDeltaClient(unittest.TestCase):
    @patch("delta_vault.client.DeltaFetcher")
    def test_get_products(self, mock_fetcher_class):
        mock_fetcher = mock_fetcher_class.return_value
        mock_fetcher.get_products.return_value = [
            {"id": 1, "symbol": "BTCUSD"},
            {"id": 2, "symbol": "ETHUSD"},
        ]

        client = DeltaClient()
        df = client.get_products()

        self.assertEqual(len(df), 2)
        self.assertIn("symbol", df.columns)

    @patch("delta_vault.client.DeltaFetcher")
    def test_get_candles(self, mock_fetcher_class):
        mock_fetcher = mock_fetcher_class.return_value
        mock_fetcher.get_candles.return_value = [
            {
                "time": 1792832400,
                "open": 100,
                "high": 110,
                "low": 90,
                "close": 105,
                "volume": 5,
            }
        ]

        client = DeltaClient()
        df = client.get_candles("BTCUSD", resolution="1h", days=1)

        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["symbol"], "BTCUSD")
        self.assertEqual(df.iloc[0]["close"], 105)


if __name__ == "__main__":
    unittest.main()