
import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.upstox.com/v3"
ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")


def get_candles(instrument_key, timeframe, from_date, to_date):
    if not ACCESS_TOKEN:
        raise ValueError("UPSTOX_ACCESS_TOKEN missing from .env")

    url = (
        f"{BASE_URL}/historical-candle/"
        f"{instrument_key}/{timeframe}/1/{to_date}/{from_date}"
    )

    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Accept": "application/json",
        },
        timeout=30,
    )
    response.raise_for_status()

    candles = response.json()["data"]["candles"]

    columns = [
        "timestamp", "open", "high", "low",
        "close", "volume", "open_interest",
    ]

    df = pd.DataFrame(candles, columns=columns)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    return df.sort_values("timestamp").reset_index(drop=True)


df = get_candles(
    instrument_key="NSE_EQ|INE002A01018",
    timeframe="days",
    from_date="2026-01-01",
    to_date="2026-10-26",
)

print(df.head())