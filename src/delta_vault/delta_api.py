
import json
import time
from pathlib import Path

import requests
import pandas as pd

BASE_URL = "https://api.india.delta.exchange"
OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "User-Agent": "ClubDataVault/1.0",
})


def api_get(endpoint, params=None):
    response = session.get(
        BASE_URL + endpoint,
        params=params,
        timeout=30,
    )
    print(f"HTTP {response.status_code}: {response.url}")
    response.raise_for_status()

    data = response.json()

    if data.get("success") is False:
        raise RuntimeError(f"API error: {data.get('error')}")

    return data


def fetch_all_products():
    """Follow the pagination cursor until no next page remains."""
    products = []
    cursor = None
    seen_cursors = set()

    while True:
        params = {"page_size": 100}

        if cursor:
            params["after"] = cursor

        data = api_get("/v2/products", params)
        page = data.get("result", [])
        products.extend(page)

        print(
            f"Fetched {len(page)} products; "
            f"total so far: {len(products)}"
        )

        next_cursor = data.get("meta", {}).get("after")

        if not page or not next_cursor:
            break

        if next_cursor in seen_cursors:
            print("Repeated pagination cursor; stopping safely.")
            break

        seen_cursors.add(next_cursor)
        cursor = next_cursor

    # Keep one record per product ID where possible.
    df = pd.DataFrame(products)

    if not df.empty and "id" in df.columns:
        df = df.drop_duplicates(subset=["id"], keep="last")

    df.to_csv(OUTPUT_DIR / "all_products.csv", index=False)

    with open(
        OUTPUT_DIR / "all_products.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(products, file, indent=2)

    print(f"\nUnique products saved: {len(df)}")

    if not df.empty:
        for column in ("contract_type", "state"):
            if column in df.columns:
                print(f"\n{column} counts:")
                print(df[column].value_counts(dropna=False))

    return df


def fetch_candles(symbol, resolution="1h", hours=24):
    """Fetch a recent sample of historical candles."""
    end = int(time.time())
    start = end - hours * 3600

    data = api_get(
        "/v2/history/candles",
        {
            "symbol": symbol,
            "resolution": resolution,
            "start": start,
            "end": end,
        },
    )

    candles = data.get("result", [])
    df = pd.DataFrame(candles)

    if df.empty:
        print(f"No candles returned for {symbol}.")
        return df

    df = df.rename(columns={"time": "timestamp"})

    if "timestamp" not in df.columns:
        raise ValueError("Candle response has no time field.")

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        unit="s",
        utc=True,
        errors="coerce",
    )

    for column in ("open", "high", "low", "close", "volume"):
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column], errors="coerce"
            )

    required = [
        "timestamp", "open", "high", "low", "close", "volume"
    ]
    missing = [column for column in required if column not in df]

    if missing:
        raise ValueError(f"Missing candle fields: {missing}")

    df = df.dropna(subset=required)
    df = df.drop_duplicates(subset=["timestamp"], keep="last")
    df = df.sort_values("timestamp").reset_index(drop=True)

    df.insert(1, "symbol", symbol)

    df.to_csv(OUTPUT_DIR / "sample_candles.csv", index=False)

    print(f"\nSymbol: {symbol}")
    print(f"Candles returned: {len(df)}")
    print(df.head(10).to_string(index=False))

    return df


if __name__ == "__main__":
    products = fetch_all_products()

    # Prefer a live perpetual future for a basic price-history test.
    candidates = products

    if "state" in candidates.columns:
        live = candidates[
            candidates["state"].astype(str).str.lower() == "live"
        ]
        if not live.empty:
            candidates = live

    if "contract_type" in candidates.columns:
        futures = candidates[
            candidates["contract_type"].astype(str).str.lower()
            == "perpetual_futures"
        ]

        if not futures.empty:
            candidates = futures

    if not candidates.empty and "symbol" in candidates.columns:
        symbol = candidates.iloc[0]["symbol"]
        fetch_candles(str(symbol), resolution="1h", hours=24)
    else:
        print("No suitable product found for the candle test.")
        print("Check data/all_products.csv")
