from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

from club_data_vault.api import app
from club_data_vault.client import DataClient


def sample_frame():
    return pd.DataFrame({
        "timestamp": pd.to_datetime(["2024-01-01"], utc=True),
        "exchange": ["binance"], "symbol": ["BTCUSDT"], "interval": ["1d"],
        "open": [100.0], "high": [110.0], "low": [90.0], "close": [105.0], "volume": [12.0],
    })


def test_client_loads_and_filters_a_parquet_file():
    class Store:
        def catalog(self):
            return [{"instrument_id": "binance:BTCUSDT", "exchange": "binance", "symbol": "BTCUSDT", "intervals": ["1d"], "paths": ["data.bin"]}]

        def download(self, path):
            return path

    with patch("club_data_vault.client.pd.read_parquet", return_value=sample_frame()):
        result = DataClient(Store()).load(instrument="binance:BTCUSDT", interval="1d")
    assert len(result) == 1
    assert result.iloc[0]["symbol"] == "BTCUSDT"


def test_client_resamples_only_the_selected_source_interval():
    minute_frame = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=5, freq="min", tz="UTC"),
        "open": [1, 2, 3, 4, 5], "high": [2, 3, 4, 5, 6],
        "low": [0, 1, 2, 3, 4], "close": [1, 2, 3, 4, 5], "volume": [1, 1, 1, 1, 1],
    })

    class Store:
        def catalog(self):
            return [{"instrument_id": "delta:BTCUSD", "exchange": "delta", "symbol": "BTCUSD", "intervals": ["1m"], "paths": ["Delta_Exchange/data/BTCUSD/2024-01.parquet"]}]

        def download(self, path):
            return path

    with patch("club_data_vault.client.pd.read_parquet", return_value=minute_frame):
        result = DataClient(Store()).load(instrument="delta:BTCUSD", interval="5m")
    assert len(result) == 1
    assert result.iloc[0]["open"] == 1
    assert result.iloc[0]["close"] == 5
    assert result.iloc[0]["volume"] == 5
    assert result.iloc[0]["interval"] == "5m"


def test_api_health_and_market_data():
    class Client:
        def catalog(self):
            return [{"instrument_id": "binance:BTCUSDT", "exchange": "binance"}]

        def load(self, **filters):
            return sample_frame()

    with patch("club_data_vault.api.DataClient", Client):
        client = TestClient(app)
        assert client.get("/health").json() == {"status": "ok"}
        response = client.get("/v1/market-data?instrument=binance:BTCUSDT")
    assert response.status_code == 200
    assert response.json()["data"][0]["symbol"] == "BTCUSDT"
