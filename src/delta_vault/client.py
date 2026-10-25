from datetime import datetime, timedelta, timezone

import pandas as pd

from .cleaning import clean_candles, clean_products
from .fetchers import DeltaFetcher


class DeltaClient:
    """Convenient interface for fetching cleaned market data."""

    def __init__(self, timeout: int = 20):
        self._fetcher = DeltaFetcher(timeout=timeout)

    def get_products(self) -> pd.DataFrame:
        """Return all products as a DataFrame."""
        products = self._fetcher.get_products()
        return clean_products(products)

    def get_candles(
        self,
        symbol: str,
        resolution: str = "1h",
        days: int = 1,
    ) -> pd.DataFrame:
        """Return cleaned historical OHLCV candles."""
        candles = self._fetcher.get_candles(
            symbol=symbol,
            resolution=resolution,
            days=days,
        )
        return clean_candles(candles, symbol=symbol)

    def get_tickers(self) -> pd.DataFrame:
        """Return ticker records as a DataFrame."""
        return pd.DataFrame(self._fetcher.get_tickers())

    def save_candles(
        self,
        symbol: str,
        resolution: str = "1h",
        days: int = 1,
        path: str = "candles.parquet",
    ) -> pd.DataFrame:
        """Fetch candles and optionally save them to Parquet or CSV."""
        df = self.get_candles(symbol, resolution, days)

        if path.lower().endswith(".csv"):
            df.to_csv(path, index=False)
        elif path.lower().endswith((".parquet", ".pq")):
            df.to_parquet(path, index=False)
        else:
            raise ValueError("File path must end in .csv, .parquet, or .pq.")

        return df

    def close(self) -> None:
        """Close the HTTP session."""
        self._fetcher.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()