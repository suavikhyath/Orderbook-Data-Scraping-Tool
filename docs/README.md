# Delta Vault

A reusable Python package for fetching and cleaning public
market data from Delta Exchange India.

## Features

- Fetch all available products
- Fetch historical OHLCV candles
- Fetch ticker data
- Convert responses to Pandas DataFrames
- Remove duplicate records
- Normalize timestamps to UTC
- Save data as CSV or Parquet

## Installation

Clone the repository and install it:

    python -m pip install -e .

For development and testing:

    python -m pip install -e ".[dev]"

## Usage

    from delta_vault import DeltaClient

    with DeltaClient() as delta:
        products = delta.get_products()
        candles = delta.get_candles(
            "BTCUSD",
            resolution="1h",
            days=30
        )

## Save data

    delta = DeltaClient()
    df = delta.save_candles(
        "BTCUSD",
        resolution="1h",
        days=7,
        path="btc_candles.parquet"
    )
    delta.close()

## Run tests

    python -m pytest

## Notes

Public market-data endpoints do not require Delta Exchange API
credentials. Requests are subject to the exchange's rate limits.