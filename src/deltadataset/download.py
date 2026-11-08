
import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests


# ==================================================
# PATHS - RELATIVE TO THIS FILE
# ==================================================

BASE_DIR = Path(__file__).resolve().parent

CONFIG_FILE = BASE_DIR / "config" / "coins.json"
DATA_DIR = BASE_DIR / "data" / "crypto-top20-1m"


# ==================================================
# API CONFIGURATION
# ==================================================

COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/coins/markets"
)

DELTA_BASE = "https://api.india.delta.exchange"

LOOKBACK_DAYS = 730
RESOLUTION = "1m"

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "User-Agent": "crypto-data-vault/1.0",
})


# ==================================================
# HTTP
# ==================================================

def get_json(url, params=None):

    for attempt in range(6):

        try:
            response = session.get(
                url,
                params=params,
                timeout=30,
            )

            if response.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue

            response.raise_for_status()
            return response.json()

        except requests.RequestException:

            if attempt == 5:
                raise

            time.sleep(2 * (attempt + 1))

    raise RuntimeError(f"Request failed: {url}")


# ==================================================
# COINGECKO TOP 20
# ==================================================

def get_top20():

    print("Fetching CoinGecko top 20...")

    return get_json(
        COINGECKO_URL,
        {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 20,
            "page": 1,
            "sparkline": "false",
        },
    )


# ==================================================
# DELTA PRODUCTS
# ==================================================

def get_products():

    print("Fetching Delta products...")

    products = []
    after = None
    seen = set()

    while True:

        params = {"page_size": 100}

        if after:
            params["after"] = after

        response = get_json(
            f"{DELTA_BASE}/v2/products",
            params,
        )

        if not response.get("success"):
            raise RuntimeError(
                f"Delta products API error: {response}"
            )

        page = response.get("result", [])
        products.extend(page)

        print(f"Retrieved {len(page)} products")

        next_cursor = response.get(
            "meta", {}
        ).get("after")

        if not next_cursor or next_cursor in seen:
            break

        seen.add(next_cursor)
        after = next_cursor

    print("Total products:", len(products))

    return products


# ==================================================
# PREPARE COIN CONFIG
# ==================================================

def prepare():

    coins = get_top20()
    products = get_products()

    output = []

    for rank, coin in enumerate(coins, start=1):

        ticker = coin["symbol"].upper()
        candidates = []

        for product in products:

            underlying = str(
                product.get("underlying_asset", {}).get("symbol", "")
            ).upper()

            if underlying != ticker:
                continue

            if product.get("contract_type") != "perpetual_futures":
                continue

            if product.get("state") != "live":
                continue

            if product.get("trading_status") != "operational":
                continue

            candidates.append({
                "delta_symbol": product.get("symbol"),
                "state": product.get("state"),
                "trading_status": product.get("trading_status"),
                "contract_type": product.get("contract_type"),
                "quoting_asset": product.get(
                    "quoting_asset", {}
                ).get("symbol"),
            })

        # Don't guess if multiple contracts match.
        selected = (
            candidates[0]["delta_symbol"]
            if len(candidates) == 1
            else None
        )

        output.append({
            "rank": rank,
            "id": coin["id"],
            "name": coin["name"],
            "symbol": ticker,
            "market_cap_usd": coin.get("market_cap"),
            "delta_symbol": selected,
            "delta_candidates": candidates,
        })

    CONFIG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    config = {
        "source": "CoinGecko",
        "ranking": "market_cap_desc",
        "snapshot_date": datetime.now(
            timezone.utc
        ).isoformat(),
        "resolution": RESOLUTION,
        "lookback_days": LOOKBACK_DAYS,
        "coins": output,
    }

    CONFIG_FILE.write_text(
        json.dumps(config, indent=2)
    )

    print("\nTOP 20 MAPPING")
    print("-" * 65)

    for coin in output:

        print(
            f'{coin["rank"]:2}. '
            f'{coin["name"]:20} '
            f'{coin["symbol"]:8} -> '
            f'{coin["delta_symbol"]}'
        )

        if len(coin["delta_candidates"]) > 1:
            print("   Multiple contracts; manual selection required.")

    supported = sum(
        bool(c["delta_symbol"]) for c in output
    )

    print("-" * 65)
    print("Global top 20:", len(output))
    print("Automatically mapped:", supported)
    print("Unresolved:", len(output) - supported)
    print("\nSaved:", CONFIG_FILE)


# ==================================================
# DOWNLOAD CANDLES
# ==================================================

def download_candles(symbol, start, end):

    rows = []
    cursor = int(start)
    end = int(end)

    # Maximum 2,000 one-minute candles per request.
    chunk_seconds = 1999 * 60

    while cursor < end:

        chunk_end = min(
            cursor + chunk_seconds,
            end,
        )

        response = get_json(
            f"{DELTA_BASE}/v2/history/candles",
            {
                "resolution": RESOLUTION,
                "symbol": symbol,
                "start": cursor,
                "end": chunk_end,
            },
        )

        if not response.get("success"):
            raise RuntimeError(
                f"Candle API error for {symbol}: {response}"
            )

        rows.extend(response.get("result", []))

        cursor = chunk_end + 60

        time.sleep(0.15)

    return rows


# ==================================================
# MONTH RANGES
# ==================================================

def month_ranges(start, end):

    current = start.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    while current < end:

        if current.month == 12:

            next_month = current.replace(
                year=current.year + 1,
                month=1,
            )

        else:

            next_month = current.replace(
                month=current.month + 1,
            )

        yield max(current, start), min(next_month, end)

        current = next_month


# ==================================================
# DOWNLOAD DATASET
# ==================================================

def download():

    if not CONFIG_FILE.exists():

        raise FileNotFoundError(
            f"Missing configuration: {CONFIG_FILE}\n"
            "Run download.py --prepare first."
        )

    config = json.loads(
        CONFIG_FILE.read_text()
    )

    selected = [
        coin for coin in config["coins"]
        if coin.get("delta_symbol")
    ]

    if not selected:

        raise RuntimeError(
            "No Delta symbols configured. "
            "Run --prepare and inspect coins.json."
        )

    end = datetime.now(timezone.utc).replace(
        second=0,
        microsecond=0,
    )

    start = end - timedelta(
        days=LOOKBACK_DAYS
    )

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("\nDOWNLOAD CONFIGURATION")
    print("-" * 50)
    print("Start:", start)
    print("End:", end)
    print("Resolution:", RESOLUTION)
    print("Supported coins:", len(selected))
    print("Output:", DATA_DIR)
    print("-" * 50)

    for coin in selected:

        symbol = coin["delta_symbol"]

        folder = DATA_DIR / symbol

        folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        print(
            f"\nDownloading {coin['name']} ({symbol})"
        )

        for month_start, month_end in month_ranges(
            start, end
        ):

            filename = (
                f"{month_start.year}-"
                f"{month_start.month:02d}.parquet"
            )

            path = folder / filename

            print(f"  {filename}")

            rows = download_candles(
                symbol,
                month_start.timestamp(),
                month_end.timestamp(),
            )

            if not rows:
                print("    No candles returned.")
                continue

            df = pd.DataFrame(rows)

            # Support both response timestamp field names.
            time_column = (
                "time"
                if "time" in df.columns
                else "timestamp"
            )

            required = {
                time_column,
                "open",
                "high",
                "low",
                "close",
                "volume",
            }

            missing = required - set(df.columns)

            if missing:

                raise ValueError(
                    f"Unexpected candle response for {symbol}. "
                    f"Missing: {missing}. "
                    f"Received: {list(df.columns)}"
                )

            df["timestamp"] = pd.to_datetime(
                df[time_column],
                unit="s",
                utc=True,
            )

            df["symbol"] = symbol

            for col in [
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]:

                df[col] = pd.to_numeric(
                    df[col],
                    errors="coerce",
                )

            df = df[
                [
                    "timestamp",
                    "symbol",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ]
            ]

            df = df.dropna(
                subset=[
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                ]
            )

            # Keep only candles in the requested month.
            df = df[
                (df["timestamp"] >= month_start)
                & (df["timestamp"] < month_end)
            ]

            df = df.drop_duplicates(
                subset=["timestamp", "symbol"]
            )

            df = df.sort_values("timestamp")

            if df.empty:
                print("    No valid candles.")
                continue

            df.to_parquet(
                path,
                index=False,
                compression="zstd",
            )

            print(f"    Saved {len(df):,} candles")

    print("\nDownload completed!")
    print("Location:", DATA_DIR)


# ==================================================
# MAIN
# ==================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Generate current CoinGecko top 20 configuration",
    )

    args = parser.parse_args()

    if args.prepare:
        prepare()
    else:
        download()
