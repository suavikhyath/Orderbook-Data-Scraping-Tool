# src/delta_vault/fetchers.py

from datetime import datetime, timedelta, timezone

import requests

from .exceptions import DeltaAPIError

BASE_URL = "https://api.india.delta.exchange"
TIMEOUT = 20
MAX_CANDLES = 2000


class DeltaFetcher:
    """Low-level HTTP client for public Delta Exchange market data."""

    def __init__(self, base_url: str = BASE_URL, timeout: int = TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def get_json(self, endpoint: str, params: dict | None = None) -> dict:
        """Request an endpoint and validate the JSON response."""
        try:
            response = self.session.get(
                f"{self.base_url}{endpoint}",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise DeltaAPIError(f"Delta API request failed: {exc}") from exc
        except ValueError as exc:
            raise DeltaAPIError("Delta API returned invalid JSON.") from exc

        if not isinstance(data, dict):
            raise DeltaAPIError("Unexpected API response format.")

        if data.get("success") is False:
            raise DeltaAPIError(f"Delta API error: {data.get('error', data)}")

        return data

    def get_products(self, page_size: int = 100) -> list[dict]:
        """Fetch all product pages using the API's after cursor."""
        products = []
        after = None
        seen_cursors = set()

        while True:
            params = {"page_size": page_size}
            if after:
                params["after"] = after

            data = self.get_json("/v2/products", params)
            result = data.get("result", [])

            if not isinstance(result, list):
                raise DeltaAPIError("Unexpected products response format.")

            products.extend(result)

            meta = data.get("meta") or {}
            next_after = meta.get("after")

            if not next_after or not result or next_after in seen_cursors:
                break

            seen_cursors.add(next_after)
            after = next_after

        return products

    def get_candles(
        self,
        symbol: str,
        resolution: str = "1h",
        days: int = 1,
    ) -> list[dict]:
        """Fetch candle history, splitting large requests into safe chunks."""
        resolutions = {
            "1m": 60,
            "3m": 180,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "2h": 7200,
            "4h": 14400,
            "6h": 21600,
            "1d": 86400,
            "1w": 604800,
        }

        if resolution not in resolutions:
            raise ValueError(
                f"Unsupported resolution {resolution!r}. "
                f"Choose from {', '.join(resolutions)}."
            )

        if not symbol or not symbol.strip():
            raise ValueError("symbol must not be empty.")

        if isinstance(days, bool) or not isinstance(days, int) or days <= 0:
            raise ValueError("days must be a positive integer.")

        interval = resolutions[resolution]
        end_time = int(datetime.now(timezone.utc).timestamp())
        start_time = int(
            (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
        )

        # The endpoint returns at most 2000 candles per request.
        chunk_seconds = MAX_CANDLES * interval
        candles = []
        chunk_start = start_time

        while chunk_start < end_time:
            chunk_end = min(chunk_start + chunk_seconds, end_time)

            data = self.get_json(
                "/v2/history/candles",
                {
                    "symbol": symbol,
                    "resolution": resolution,
                    "start": chunk_start,
                    "end": chunk_end,
                },
            )

            result = data.get("result", [])
            if not isinstance(result, list):
                raise DeltaAPIError("Unexpected candles response format.")

            candles.extend(result)
            chunk_start = chunk_end

        return candles

    def get_tickers(self) -> list[dict]:
        """Fetch available ticker records."""
        data = self.get_json("/v2/tickers")
        result = data.get("result", [])

        if not isinstance(result, list):
            raise DeltaAPIError("Unexpected tickers response format.")

        return result

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()