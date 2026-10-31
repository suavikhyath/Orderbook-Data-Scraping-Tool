
import json
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
from tempfile import TemporaryDirectory
import pandas as pd
import requests

from src.delta_vault import delta_api as api


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

    @patch("src.delta_vault.delta_api.session.get")
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

    @patch("src.delta_vault.delta_api.session.get")
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



    @patch("src.delta_vault.delta_api.session.get")
    def test_api_get_timeout(self, mock_get):
        """Network timeouts should propagate."""
        mock_get.side_effect = requests.Timeout("Request timed out")

        with self.assertRaises(requests.Timeout):
            api.api_get("/v2/products")

    # --------------------------------------------------
    # PRODUCT DATA TESTS
    # --------------------------------------------------

    @patch("src.delta_vault.delta_api.api_get")
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

    @patch("src.delta_vault.delta_api.api_get")
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

    @patch("src.delta_vault.delta_api.api_get")
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

    @patch("src.delta_vault.delta_api.api_get")
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

    @patch("src.delta_vault.delta_api.api_get")
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

        # ==============================
        # Additional Edge Case Tests
        # ==============================

    @patch("src.delta_vault.delta_api.session.get")
    def test_api_get_api_error(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": False,
            "error": "Invalid request"
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with self.assertRaises(RuntimeError):
            api.api_get("/v2/products")


    @patch("src.delta_vault.delta_api.session.get")
    def test_api_get_malformed_json(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = requests.exceptions.JSONDecodeError(
            "Invalid JSON", "not valid json", 0
        )
        mock_get.return_value = mock_response

        with self.assertRaises(requests.exceptions.JSONDecodeError):
            api.api_get("/v2/products")

    @patch("src.delta_vault.delta_api.session.get")
    def test_api_get_connection_error(self, mock_get):
        mock_get.side_effect = requests.ConnectionError(
            "Connection failed"
        )

        with self.assertRaises(requests.ConnectionError):
            api.api_get("/v2/products")


    @patch("src.delta_vault.delta_api.api_get")
    def test_products_missing_result(self, mock_api_get):
        mock_api_get.return_value = {
            "success": True,
            "meta": {}
        }

        with TemporaryDirectory() as tmp:
            original_dir = api.OUTPUT_DIR
            api.OUTPUT_DIR = Path(tmp)

            try:
                products = api.fetch_all_products()
                self.assertTrue(products.empty)
            finally:
                api.OUTPUT_DIR = original_dir

    @patch("src.delta_vault.delta_api.api_get")
    def test_empty_products_response(self, mock_api_get):
        mock_api_get.return_value = {
            "success": True,
            "result": [],
            "meta": {}
        }

        with TemporaryDirectory() as tmp:
            original_dir = api.OUTPUT_DIR
            api.OUTPUT_DIR = Path(tmp)

            try:
                products = api.fetch_all_products()
                self.assertTrue(products.empty)
            finally:
                api.OUTPUT_DIR = original_dir

    @patch("src.delta_vault.delta_api.api_get")
    def test_repeated_pagination_cursor(self, mock_api_get):
        response = {
            "success": True,
            "result": [self.sample_products[0]],
            "meta": {"after": "cursor-2"}
        }
        mock_api_get.side_effect = [response, response]

        with TemporaryDirectory() as tmp:
            original_dir = api.OUTPUT_DIR
            api.OUTPUT_DIR = Path(tmp)

            try:
                api.fetch_all_products()
                self.assertEqual(mock_api_get.call_count, 2)
            finally:
                api.OUTPUT_DIR = original_dir


    @patch("src.delta_vault.delta_api.api_get")
    def test_missing_candle_fields(self, mock_api_get):
        mock_api_get.return_value = {
            "success": True,
            "result": [{
                "time": 1792832400,
                "open": 10
            }]
        }

        with self.assertRaises(ValueError):
            api.fetch_candles(
                "IOSTUSD", resolution="1h", hours=24
            )

    @patch("src.delta_vault.delta_api.api_get")
    def test_invalid_candle_values(self, mock_api_get):
        mock_api_get.return_value = {
            "success": True,
            "result": [{
                "time": 1792832400,
                "open": "invalid",
                "high": 12,
                "low": 9,
                "close": 11,
                "volume": 100
            }]
        }

        df = api.fetch_candles(
            "IOSTUSD", resolution="1h", hours=24
        )

        self.assertTrue(df.empty)

    @patch("src.delta_vault.delta_api.api_get")
    def test_invalid_timestamp(self, mock_api_get):
        mock_api_get.return_value = {
            "success": True,
            "result": [{
                "time": "invalid",
                "open": 10,
                "high": 12,
                "low": 9,
                "close": 11,
                "volume": 100
            }]
        }

        df = api.fetch_candles(
            "IOSTUSD", resolution="1h", hours=24
        )

        self.assertTrue(df.empty)

    @patch("src.delta_vault.delta_api.api_get")
    def test_missing_volume(self, mock_api_get):
        mock_api_get.return_value = {
            "success": True,
            "result": [{
                "time": 1792832400,
                "open": 10,
                "high": 12,
                "low": 9,
                "close": 11
            }]
        }

        with self.assertRaises(ValueError):
            api.fetch_candles(
                "IOSTUSD", resolution="1h", hours=24
            )

    def test_api_get_http_errors(self):
        error_codes = [
            400, 401, 403, 422,
            429,
            500, 502, 503, 504
        ]

        for status_code in error_codes:
            with self.subTest(status_code=status_code):
                mock_response = Mock()
                mock_response.status_code = status_code
                mock_response.url = "https://api.example.com/v2/products"

                mock_response.raise_for_status.side_effect = requests.HTTPError(
                    f"{status_code} HTTP Error"
                )

                with patch.object(
                        api.session, "get", return_value=mock_response
                ):
                    with self.assertRaises(requests.HTTPError):
                        api.api_get("/v2/products")

    # ==============================
    # Zero and Negative Interval Tests
    # ==============================

    @patch("src.delta_vault.delta_api.time.time", return_value=1700000000)
    @patch("src.delta_vault.delta_api.api_get")
    def test_fetch_candles_zero_interval(self, mock_api_get, mock_time):
        mock_api_get.return_value = {"result": []}

        api.fetch_candles("IOSTUSD", hours=0)

        expected_params = {
            "symbol": "IOSTUSD",
            "resolution": "1h",
            "start": 1700000000,
            "end": 1700000000,
        }

        mock_api_get.assert_called_once_with(
            "/v2/history/candles", expected_params
        )

    @patch("src.delta_vault.delta_api.time.time", return_value=1700000000)
    @patch("src.delta_vault.delta_api.api_get")
    def test_fetch_candles_negative_interval(self, mock_api_get, mock_time):
        mock_api_get.return_value = {"result": []}

        api.fetch_candles("IOSTUSD", hours=-24)

        expected_params = {
            "symbol": "IOSTUSD",
            "resolution": "1h",
            "start": 1700000000 + (24 * 3600),
            "end": 1700000000,
        }

        mock_api_get.assert_called_once_with(
            "/v2/history/candles", expected_params
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)
