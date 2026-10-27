
import pandas as pd
import pytest
import requests

from delta_vault.upstox import upstox_api as api


@pytest.fixture
def mock_candles():
    return [
        [
            "2026-01-02T00:00:00+05:30",
            1400.0, 1450.0, 1390.0, 1430.0, 10000, 0
        ],
        [
            "2026-01-01T00:00:00+05:30",
            1380.0, 1420.0, 1370.0, 1400.0, 8000, 0
        ],
    ]


def test_get_candles_success(monkeypatch, mock_candles):
    monkeypatch.setattr(api, "ACCESS_TOKEN", "test-token")

    def mock_get(url, headers, timeout):
        assert "NSE_EQ|INE002A01018" in url
        assert headers["Authorization"] == "Bearer test-token"
        assert timeout == 30

        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"data": {"candles": mock_candles}}

        return MockResponse()

    monkeypatch.setattr(api.requests, "get", mock_get)

    df = api.get_candles(
        "NSE_EQ|INE002A01018",
        "days",
        "2026-01-01",
        "2026-01-02",
    )

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == [
        "timestamp", "open", "high", "low",
        "close", "volume", "open_interest",
    ]
    assert df["timestamp"].is_monotonic_increasing
    assert df.iloc[0]["close"] == 1400.0


def test_missing_access_token(monkeypatch):
    monkeypatch.setattr(api, "ACCESS_TOKEN", None)

    with pytest.raises(ValueError, match="UPSTOX_ACCESS_TOKEN"):
        api.get_candles(
            "NSE_EQ|INE002A01018",
            "days",
            "2026-01-01",
            "2026-01-02",
        )


def test_http_error_propagates(monkeypatch):
    monkeypatch.setattr(api, "ACCESS_TOKEN", "test-token")

    def mock_get(url, headers, timeout):
        response = requests.Response()
        response.status_code = 401
        response._content = b"Unauthorized"
        response.url = url
        return response

    monkeypatch.setattr(api.requests, "get", mock_get)

    with pytest.raises(requests.HTTPError):
        api.get_candles(
            "NSE_EQ|INE002A01018",
            "days",
            "2026-01-01",
            "2026-01-02",
        )


def test_empty_candle_response(monkeypatch):
    monkeypatch.setattr(api, "ACCESS_TOKEN", "test-token")

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": {"candles": []}}

    monkeypatch.setattr(
        api.requests, "get", lambda *args, **kwargs: MockResponse()
    )

    df = api.get_candles(
        "NSE_EQ|INE002A01018",
        "days",
        "2026-01-01",
        "2026-01-02",
    )

    assert df.empty
    assert "timestamp" in df.columns
