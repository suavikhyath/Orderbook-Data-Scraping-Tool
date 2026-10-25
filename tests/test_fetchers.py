import unittest
from unittest.mock import Mock, patch

from delta_vault.exceptions import DeltaAPIError
from delta_vault.fetchers import DeltaFetcher


class TestFetchers(unittest.TestCase):
    def setUp(self):
        self.fetcher = DeltaFetcher()

    def tearDown(self):
        self.fetcher.close()

    @patch("delta_vault.fetchers.requests.Session.get")
    def test_get_json_success(self, mock_get):
        response = Mock()
        response.json.return_value = {
            "success": True,
            "result": [{"id": 1}],
        }
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        result = self.fetcher.get_json("/v2/products")

        self.assertEqual(result["result"][0]["id"], 1)

    @patch("delta_vault.fetchers.requests.Session.get")
    def test_get_json_api_error(self, mock_get):
        response = Mock()
        response.json.return_value = {
            "success": False,
            "error": {"code": "invalid_request"},
        }
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        with self.assertRaises(DeltaAPIError):
            self.fetcher.get_json("/v2/products")

    @patch.object(DeltaFetcher, "get_json")
    def test_products_pagination(self, mock_json):
        mock_json.side_effect = [
            {
                "success": True,
                "result": [{"id": 1}],
                "meta": {"after": "cursor-2"},
            },
            {
                "success": True,
                "result": [{"id": 2}],
                "meta": {"after": None},
            },
        ]

        products = self.fetcher.get_products()

        self.assertEqual(len(products), 2)
        self.assertEqual(products[1]["id"], 2)

    @patch.object(DeltaFetcher, "get_json")
    def test_candles_fetch(self, mock_json):
        mock_json.return_value = {
            "success": True,
            "result": [
                {
                    "time": 1792832400,
                    "open": 100,
                    "high": 110,
                    "low": 90,
                    "close": 105,
                    "volume": 5,
                }
            ],
        }

        candles = self.fetcher.get_candles("BTCUSD", "1h", days=1)

        self.assertEqual(len(candles), 1)
        self.assertEqual(candles[0]["close"], 105)

    def test_invalid_resolution(self):
        with self.assertRaises(ValueError):
            self.fetcher.get_candles("BTCUSD", "7d", days=1)


if __name__ == "__main__":
    unittest.main()