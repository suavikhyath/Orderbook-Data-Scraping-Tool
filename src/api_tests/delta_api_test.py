
import json
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import requests

import main_api as api


class TestDeltaAPI(unittest.TestCase):

    def setUp(self):
        """Prepare sample API responses for tests."""
        self.sample_candles = [
            {
                "time": 1792832400,
                "open": 0.000773,
                "high": 0.000773,
                "low": 0.000751,
                "close": 0.000753,
                "volume": 1172,
            },
            {
                "time": 1792836000,
                "open": 0.000755,
                "high": 0.000762,
                "low": 0.000754,
                "close": 0.000762,
                "volume": 403,
            },
        ]

        self.sample_products = [
            {
                "id": 1,
                "symbol": "IOSTUSD",
                "contract_type": "perpetual_futures",
                "tick_size": "0.000001",
                "state": "live",
            },
            {
                "id": 2,
                "symbol": "BTCUSD",
                "contract_type": "perpetual_futures",
                "tick_size": "0.5",
                "state": "live",
            },
        ]

    # --------------------------------------------------
    # API REQUEST TESTS
    # --------------------------------------------------

    @patch("main_api.session.get")
    def test_api_get_success(self, mock_get):
        """A successful API response should return JSON."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "result": self.sample_products,
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = api.api_get("/v2/products", {"page_size": 100})

        self.assertTrue(result["success"])
        self.assertEqual(len(result["result"]), 2)
        mock_get.assert_called_once()

    @patch("main_api.session.get")
    def test_api_get_http_error(self, mock_get):
        """HTTP errors should propagate to the caller."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = (
            requests.HTTPError("404 Not Found")
        )
        mock_get.return_value = mock_response

        with self.assertRaises(requests.HTTPError):
            api.api_get("/invalid-endpoint")

    @patch("main_api.session.get")
    def test_api_get_timeout(self, mock_get):
        """Network timeouts should propagate."""
        mock_get.side_effect = requests.Timeout("Request timed out")

        with self.assertRaises(requests.Timeout):
            api.api_get("/v2/products")

    # --------------------------------------------------
    # PRODUCT DATA TESTS
    # --------------------------------------------------

    @patch("main_api.api_get")
    def test_fetch_products(self, mock_api_get):
        """Product responses should be saved and returned."""
        mock_api_get.return_value = {
            "success": True,
            "result": self.sample_products,
            "meta": {},
        }

        with TemporaryDirectory() as tmp:
            original_dir = api.OUTPUT_DIR
            api.OUTPUT_DIR = Path(tmp)

            try:
                products = api.fetch_all_products()

                self.assertEqual(len(products), 2)
                self.assertIn("symbol", products.columns)
                self.assertTrue(
                    (Path(tmp) / "all_products.csv").exists()
                )
                self.assertTrue(
                    (Path(tmp) / "all_products.json").exists()
                )
            finally:
                api.OUTPUT_DIR = original_dir

    @patch("main_api.api_get")
    def test_product_pagination(self, mock_api_get):
        """The next cursor should fetch the following page."""
        mock_api_get.side_effect = [
            {
                "success": True,
                "result": [self.sample_products[0]],
                "meta": {"after": "cursor-2"},
            },
            {
                "success": True,
                "result": [self.sample_products[1]],
                "meta": {},
            },
        ]

        with TemporaryDirectory() as tmp:
            original_dir = api.OUTPUT_DIR
            api.OUTPUT_DIR = Path(tmp)

            try:
                products = api.fetch_all_products()

                self.assertEqual(len(products), 2)
                self.assertEqual(mock_api_get.call_count, 2)

                second_call_params = mock_api_get.call_args_list[1].args[1]
                self.assertEqual(second_call_params["after"], "cursor-2")
            finally:
                api.OUTPUT_DIR = original_dir

    # --------------------------------------------------
    # CANDLE DATA TESTS
    # --------------------------------------------------

    @patch("main_api.api_get")
    def test_fetch_candles(self, mock_api_get):
        """Candle data should be parsed, cleaned and saved."""
        mock_api_get.return_value = {
            "success": True,
            "result": self.sample_candles,
        }

        with TemporaryDirectory() as tmp:
            original_dir = api.OUTPUT_DIR
            api.OUTPUT_DIR = Path(tmp)

            try:
                df = api.fetch_candles(
                    "IOSTUSD",
                    resolution="1h",
                    hours=24,
                )

                self.assertEqual(len(df), 2)
                self.assertIn("timestamp", df.columns)
                self.assertIn("symbol", df.columns)
                self.assertTrue(
                    (Path(tmp) / "sample_candles.csv").exists()
                )
                self.assertTrue(
                    (df["symbol"] == "IOSTUSD").all()
                )
            finally:
                api.OUTPUT_DIR = original_dir

    @patch("main_api.api_get")
    def test_empty_candle_response(self, mock_api_get):
        """An empty candle response should return an empty DataFrame."""
        mock_api_get.return_value = {
            "success": True,
            "result": [],
        }

        df = api.fetch_candles(
            "IOSTUSD",
            resolution="1h",
            hours=24,
        )

        self.assertTrue(df.empty)

    @patch("main_api.api_get")
    def test_missing_timestamp(self, mock_api_get):
        """Malformed candle responses should fail clearly."""
        mock_api_get.return_value = {
            "success": True,
            "result": [
                {
                    "open": 10,
                    "high": 11,
                    "low": 9,
                    "close": 10,
                    "volume": 100,
                }
            ],
        }

        with self.assertRaises(ValueError):
            api.fetch_candles(
                "IOSTUSD",
                resolution="1h",
                hours=24,
            )

    # --------------------------------------------------
    # DATA QUALITY TESTS
    # --------------------------------------------------

    def test_duplicate_candles_removed(self):
        """Duplicate timestamps should be reduced to one candle."""
        df = pd.DataFrame([
            {
                "time": 1792832400,
                "open": 10,
                "high": 12,
                "low": 9,
                "close": 11,
                "volume": 100,
            },
            {
                "time": 1792832400,
                "open": 10,
                "high": 12,
                "low": 9,
                "close": 11,
                "volume": 100,
            },
        ])

        df = df.rename(columns={"time": "timestamp"})
        df["timestamp"] = pd.to_datetime(
            df["timestamp"], unit="s", utc=True
        )
        df = df.drop_duplicates(subset=["timestamp"])

        self.assertEqual(len(df), 1)

    def test_ohlc_relationships(self):
        """Valid candles should satisfy high >= open/close and low <= them."""
        candle = {
            "open": 10,
            "high": 15,
            "low": 8,
            "close": 12,
        }

        self.assertGreaterEqual(
            candle["high"],
            max(candle["open"], candle["close"]),
        )
        self.assertLessEqual(
            candle["low"],
            min(candle["open"], candle["close"]),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
