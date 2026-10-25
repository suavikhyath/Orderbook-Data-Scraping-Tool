import pandas as pd

from .exceptions import DataValidationError


def clean_products(products: list) -> pd.DataFrame:
    """Convert product JSON records into a clean DataFrame."""
    if not products:
        return pd.DataFrame()

    df = pd.DataFrame(products)

    if "id" in df.columns:
        df = df.drop_duplicates(subset=["id"])

    if "symbol" in df.columns:
        df = df.drop_duplicates(subset=["symbol"])

    return df.reset_index(drop=True)


def clean_candles(candles: list, symbol: str) -> pd.DataFrame:
    """Convert raw candle records into a clean OHLCV DataFrame."""
    columns = [
        "timestamp", "open", "high", "low",
        "close", "volume", "symbol"
    ]

    if not candles:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(candles)

    if "time" in df.columns and "timestamp" not in df.columns:
        df = df.rename(columns={"time": "timestamp"})

    if "timestamp" not in df.columns:
        raise DataValidationError(
            "Candle data does not contain a timestamp."
        )

    # Delta candle timestamps are Unix seconds.
    df["timestamp"] = pd.to_datetime(
        pd.to_numeric(df["timestamp"], errors="coerce"),
        unit="s",
        utc=True,
    )

    numeric_columns = ["open", "high", "low", "close", "volume"]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        else:
            df[column] = float("nan")

    df = df.dropna(subset=["timestamp", *numeric_columns])

    df = df.drop_duplicates(subset=["timestamp"], keep="last")
    df = df.sort_values("timestamp")
    df["symbol"] = symbol

    return df[columns].reset_index(drop=True)