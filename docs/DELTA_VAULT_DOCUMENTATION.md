# Delta Vault

**A reusable Python library for fetching and cleaning public market data
from Delta Exchange India**

Delta Vault provides a small Python interface for retrieving market data
from Delta Exchange India and returning it as Pandas DataFrames. It is
designed to be installed into other Python projects and imported
directly---without running a separate server or maintaining a REST API
of your own.

> **Current scope:** The implementation described here uses public
> market-data endpoints. Public endpoints do not require Delta Exchange
> API credentials. Requests still depend on network availability and the
> exchange API's current behavior and rate limits.

------------------------------------------------------------------------

## Contents

-   [Features](#features)
-   [How it works](#how-it-works)
-   [Project layout](#project-layout)
-   [Requirements](#requirements)
-   [Installation and development
    setup](#installation-and-development-setup)
-   [Quick start](#quick-start)
-   [API reference](#api-reference)
-   [Working with the returned
    DataFrames](#working-with-the-returned-dataframes)
-   [Saving candle data](#saving-candle-data)
-   [Using Delta Vault from another
    project](#using-delta-vault-from-another-project)
-   [Testing](#testing)
-   [Building a distribution](#building-a-distribution)
-   [Errors and troubleshooting](#errors-and-troubleshooting)
-   [Configuration and limitations](#configuration-and-limitations)
-   [Development checklist](#development-checklist)

------------------------------------------------------------------------

## Features

-   Fetch the available products from Delta Exchange India.
-   Fetch historical OHLCV candles for a symbol and resolution.
-   Fetch ticker data.
-   Return data as Pandas DataFrames.
-   Clean product results and remove duplicate product records.
-   Normalize candle timestamps to UTC.
-   Convert candle price and volume fields to numeric values.
-   Sort candles by timestamp and remove duplicate timestamps.
-   Save candle data to CSV or Parquet.
-   Reuse the package from other Python projects with a normal import.
-   Use a context manager to close the underlying HTTP session.

## How it works

The package separates HTTP requests, data cleaning, and the public
client interface:

1.  **`DeltaClient` (`client.py`)** is the main interface that other
    projects import.
2.  **`DeltaFetcher` (`fetchers.py`)** sends HTTP requests to the Delta
    Exchange India API.
3.  **`cleaning.py`** converts raw product and candle responses into
    DataFrames and applies basic normalization.
4.  **`exceptions.py`** defines package-specific exceptions for API and
    validation errors.

Typical usage:

``` python
from delta_vault import DeltaClient

with DeltaClient() as delta:
    products = delta.get_products()
    candles = delta.get_candles("BTCUSD", resolution="1h", days=7)

print(products.head())
print(candles.tail())
```

No local server needs to be started. The calling Python process makes
requests directly through the library.

## Project layout

The recommended project layout is:

``` text
data-vault/
├── src/
│   └── delta_vault/
│       ├── __init__.py
│       ├── client.py
│       ├── fetchers.py
│       ├── cleaning.py
│       └── exceptions.py
├── tests/
│   ├── test_cleaning.py
│   ├── test_client.py
│   └── test_fetchers.py
├── docs/
├── samples/
├── pyproject.toml
├── requirements.txt
├── README.md
└── .gitignore
```

The distribution/project name is **`delta-vault`**, while the Python
import name is **`delta_vault`**. Use the underscore form in Python
imports.

The `src/delta_vault/` directory name must match the import package
name. Keep the package tests under the top-level `tests/` directory so
the configured test discovery finds the intended tests.

## Requirements

The current project configuration specifies:

-   Python 3.10 or newer.
-   `requests` for HTTP requests.
-   `pandas` for DataFrames and data cleaning.
-   `pytest` for running tests.
-   `pyarrow` for Parquet support in development/testing and when saving
    Parquet files.

Install dependencies using the project's `pyproject.toml` rather than
manually installing each library.

## Installation and development setup

### 1. Open the project root

Run commands from the directory containing `pyproject.toml`:

``` bash
cd ~/COEP/QuantFinance/data-vault
```

### 2. Install the package and development dependencies

Using `uv`:

``` bash
uv pip install -e ".[dev]"
```

The `-e` option installs the local package in editable mode. Code
changes in the local source directory are then reflected without
reinstalling the package.

Alternatively, if you are using a regular Python environment with pip:

``` bash
python -m pip install -e ".[dev]"
```

### 3. Verify the import

``` bash
uv run python -c "from delta_vault import DeltaClient; print('Import successful')"
```

Expected output:

``` text
Import successful
```

If this import fails, check that `src/delta_vault/__init__.py` exists
and that the project was installed from the directory containing
`pyproject.toml`.

## Quick start

### Fetch products

``` python
from delta_vault import DeltaClient

with DeltaClient() as delta:
    products = delta.get_products()

print(products.head())
print(f"Number of products: {len(products)}")
```

`get_products()` fetches product records and returns a DataFrame. The
cleaning function removes duplicate records by `id` and then by `symbol`
when those columns are present.

### Fetch tickers

``` python
from delta_vault import DeltaClient

with DeltaClient() as delta:
    tickers = delta.get_tickers()

print(tickers.head())
print(tickers.columns.tolist())
```

`get_tickers()` returns the ticker response as a DataFrame. Unlike
candle data, the current implementation does not apply a dedicated
ticker-cleaning function.

### Fetch historical candles

``` python
from delta_vault import DeltaClient

with DeltaClient() as delta:
    candles = delta.get_candles(
        symbol="BTCUSD",
        resolution="1h",
        days=7,
    )

print(candles.tail())
```

The cleaned candle DataFrame contains these columns in this order:

  Column        Meaning
  ------------- ----------------------------------------------------
  `timestamp`   Candle timestamp converted to a UTC-aware datetime
  `open`        Opening price
  `high`        Highest price
  `low`         Lowest price
  `close`       Closing price
  `volume`      Candle volume
  `symbol`      Symbol requested from the client

The actual availability of a symbol, resolution, and historical range
depends on the exchange API.

## API reference

### `DeltaClient(timeout=20)`

Creates a client backed by an HTTP session.

``` python
from delta_vault import DeltaClient

delta = DeltaClient(timeout=20)
try:
    products = delta.get_products()
finally:
    delta.close()
```

-   **`timeout`**: HTTP request timeout in seconds. Defaults to `20`.
-   **`close()`**: Closes the underlying HTTP session.
-   **Context manager support**: `with DeltaClient() as delta:` closes
    the session when the block exits, including when an exception
    occurs.

Prefer the context manager for most uses.

### `get_products() -> pandas.DataFrame`

Fetches product records from the public products endpoint and returns a
DataFrame.

``` python
with DeltaClient() as delta:
    products = delta.get_products()
```

The fetcher follows the API's `meta.after` cursor when present and stops
when there is no next cursor, the result is empty, or a cursor repeats.

### `get_tickers() -> pandas.DataFrame`

Fetches ticker records and wraps the returned list in a DataFrame.

``` python
with DeltaClient() as delta:
    tickers = delta.get_tickers()
```

Ticker columns depend on the response returned by the exchange.

### `get_candles(symbol, resolution="1h", days=1) -> pandas.DataFrame`

Fetches historical candle data and returns cleaned OHLCV rows.

``` python
with DeltaClient() as delta:
    candles = delta.get_candles("BTCUSD", resolution="15m", days=3)
```

Parameters:

-   **`symbol`**: Non-empty market symbol, for example `BTCUSD`. The
    exchange must support the requested symbol.
-   **`resolution`**: Candle interval. The current implementation
    accepts:
    -   `1m`
    -   `3m`
    -   `5m`
    -   `15m`
    -   `30m`
    -   `1h`
    -   `2h`
    -   `4h`
    -   `6h`
    -   `1d`
    -   `1w`
-   **`days`**: Positive integer number of days to request. Defaults to
    `1`.

The fetcher splits a large requested time range into chunks of at most
2,000 candle intervals per request in the current implementation.
Results are cleaned, sorted by timestamp, and deduplicated.

Invalid resolutions, empty symbols, and non-positive or non-integer
`days` values raise `ValueError`.

### `save_candles(symbol, resolution="1h", days=1, path="candles.parquet")`

Fetches and cleans candles, saves them to disk, and returns the
DataFrame.

Save as CSV:

``` python
from delta_vault import DeltaClient

with DeltaClient() as delta:
    candles = delta.save_candles(
        "BTCUSD",
        resolution="1h",
        days=7,
        path="btc_candles.csv",
    )
```

Save as Parquet:

``` python
with DeltaClient() as delta:
    candles = delta.save_candles(
        "BTCUSD",
        resolution="1h",
        days=7,
        path="btc_candles.parquet",
    )
```

Supported suffixes are `.csv`, `.parquet`, and `.pq`. Other suffixes
raise `ValueError`. Parquet writing requires a compatible Pandas Parquet
engine such as `pyarrow`.

### Package exceptions

The package defines:

-   **`DeltaVaultError`**: Base exception for library-specific errors.
-   **`DeltaAPIError`**: Raised for HTTP request failures, invalid JSON,
    unexpected API response shapes, or API responses reporting failure.
-   **`DataValidationError`**: Raised when candle data is missing the
    required timestamp field.

Import an exception when you want to handle it explicitly:

``` python
from delta_vault import DeltaClient
from delta_vault.exceptions import DeltaAPIError

try:
    with DeltaClient() as delta:
        products = delta.get_products()
except DeltaAPIError as exc:
    print(f"Could not fetch market data: {exc}")
```

Input validation errors such as an unsupported resolution are
`ValueError`, not `DeltaAPIError`.

## Working with the returned DataFrames

### Inspect available columns

``` python
print(candles.columns)
print(candles.dtypes)
print(candles.isna().sum())
```

### Filter a date range

``` python
start = "2026-01-01"
end = "2026-02-01"

period = candles[
    (candles["timestamp"] >= start)
    & (candles["timestamp"] < end)
]
```

The `timestamp` column is UTC-aware. When comparing against dates or
times in a different timezone, convert timestamps deliberately rather
than assuming they are local time.

### Calculate a simple return

``` python
candles = candles.copy()
candles["return"] = candles["close"].pct_change()
print(candles[["timestamp", "close", "return"]].tail())
```

These examples use Pandas operations after the data has been fetched;
they are not additional features provided by Delta Vault.

## Saving candle data

CSV and Parquet files can be useful for analysis and for sharing data
with other tools.

``` python
with DeltaClient() as delta:
    candles = delta.save_candles(
        "BTCUSD",
        resolution="1h",
        days=30,
        path="data/btcusd_1h.parquet",
    )
```

Create the destination directory first if it does not exist:

``` python
from pathlib import Path

Path("data").mkdir(parents=True, exist_ok=True)
```

Then call `save_candles`. The current implementation writes to the path
provided and does not automatically create missing parent directories.

Avoid committing generated market-data files to Git unless they are
intentionally part of the repository.

## Using Delta Vault from another project

Assume the directories are siblings:

``` text
QuantFinance/
├── data-vault/
│   └── pyproject.toml
└── test/
    ├── pyproject.toml
    └── src/
        └── test/
            └── main.py
```

### 1. Initialize the consuming project if necessary

From the consuming project's root:

``` bash
cd ~/COEP/QuantFinance/test
```

If the project does not yet have a `pyproject.toml`, initialize it:

``` bash
uv init
```

Do not run `uv init` again if the project is already initialized.

### 2. Add the local package

``` bash
uv add --editable ../data-vault
```

The relative path is resolved from the consuming project's current
directory. Adjust it if your folder layout differs.

### 3. Import it in your code

``` python
from delta_vault import DeltaClient

with DeltaClient() as delta:
    products = delta.get_products()
    candles = delta.get_candles("BTCUSD", resolution="1h", days=7)

print(products.head())
print(candles.tail())
```

Run the script using the consuming project's environment:

``` bash
uv run python src/test/main.py
```

The exact script path depends on your own project structure.

### Editable installation versus a built package

-   **Editable local install** (`uv add --editable ../data-vault`) is
    convenient during development because the consuming project points
    to the working source tree.
-   **Git install** is useful when the repository is hosted remotely and
    another machine needs to install it.
-   **Built wheel** is useful for distributing a versioned package. See
    [Building a distribution](#building-a-distribution).

If the consuming project uses Git, remember that a local editable
dependency is a filesystem path; another machine will need an equivalent
path or a different distribution method.

## Testing

The project uses `pytest`.

Run all package tests from the `data-vault/` root:

``` bash
uv run python -m pytest -v
```

The expected test directory is:

``` text
tests/
├── test_cleaning.py
├── test_client.py
└── test_fetchers.py
```

The tests cover cleaning behavior, client methods, fetcher behavior, and
error handling using test fixtures and mocks. Unit tests do not by
themselves prove that the live exchange API is reachable, so a separate
smoke test can be useful.

### Import smoke test

``` bash
uv run python -c "from delta_vault import DeltaClient; print('Import successful')"
```

### Optional live API smoke test

``` bash
uv run python -c "from delta_vault import DeltaClient; d = DeltaClient(); print(d.get_products().head()); d.close()"
```

This makes a real network request. It may fail if the network is
unavailable, the API is temporarily down, the endpoint changes, or the
request is rate-limited.

## Building a distribution

Install the build tool if it is not already available:

``` bash
uv add --dev build
```

For a library repository, a build dependency can instead be managed as a
development dependency according to your preferred workflow. Then build
from the project root:

``` bash
uv build
```

The project should produce files under `dist/`, typically a wheel and a
source archive. Do not commit `dist/` unless you intentionally want
built artifacts in version control.

To inspect the build output:

``` bash
ls -lh dist/
```

A successful build verifies that the package can be packaged; it does
not guarantee that live API requests will succeed.

## Errors and troubleshooting

### `No module named 'delta_vault'`

Check these items:

1.  The source directory is named `src/delta_vault`, not
    `src/delta-exchange`.

2.  `src/delta_vault/__init__.py` exists.

3.  `pyproject.toml` is in the project root.

4.  Install the project from that root:

    ``` bash
    uv pip install -e ".[dev]"
    ```

5.  If using another project, add the dependency from that project's
    root:

    ``` bash
    uv add --editable ../data-vault
    ```

### `uv add` says no `pyproject.toml` was found

You are not in an initialized `uv` project. Change to the consuming
project's root. If it has no `pyproject.toml`, run `uv init` once and
then add the dependency.

### Pytest collects an old test that imports `main_api`

Keep package tests in the top-level `tests/` directory. Move legacy
tests that depend on old modules out of that directory, or update them
to match the new package structure. Do not delete a legacy test unless
you are sure you no longer need it.

### `No files were found in testpaths`

Check that the directory named by `testpaths` in `pyproject.toml` exists
and contains your tests. For this project, the intended setting is:

``` toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

### `DeltaAPIError`

The request may have failed because of connectivity, timeout, an HTTP
error, invalid JSON, an unexpected response shape, or an API-reported
error. Check the exception message, network connection, and current
exchange API documentation.

### No candles returned

Check that the symbol is valid, that the resolution is supported, and
that the requested date range has data. An empty result can also occur
if the exchange returns no records for the requested range.

### Parquet save fails

Install a Parquet engine in the environment running the code:

``` bash
uv add pyarrow
```

For the library's own development environment, `pyarrow` is included in
the optional `dev` dependencies described in the project configuration.

## Configuration and limitations

-   The configured API base URL is `https://api.india.delta.exchange`.
-   The current implementation uses public endpoints for products,
    tickers, and historical candles.
-   Public market-data calls do not require API credentials.
-   HTTP calls have a configurable timeout; the default is 20 seconds.
-   The library does not currently provide a server, REST API, streaming
    WebSocket client, trading order placement, or private account
    access.
-   The library's cleaning is intentionally basic. Validate data for
    your own use case before using it in financial analysis or trading
    systems.
-   API response fields, supported symbols, available historical
    periods, and rate limits can change. Consult Delta Exchange India's
    current API documentation when modifying endpoints or
    troubleshooting unexpected responses.
-   Market data is provided for informational and development purposes.
    This package does not provide investment advice or guarantee data
    completeness or accuracy.

## Development checklist

Before making a release or sharing a change:

-   [ ] Confirm the package source directory is `src/delta_vault/`.
-   [ ] Confirm the import in `src/delta_vault/__init__.py` exposes
    `DeltaClient`.
-   [ ] Run `uv run python -m pytest -v`.
-   [ ] Run the import smoke test.
-   [ ] If relevant, run a live API smoke test.
-   [ ] Run `uv build`.
-   [ ] Check `git status` and ensure `.venv/`, secrets, and unintended
    generated data are not committed.
-   [ ] Update this documentation when public methods, parameters,
    supported resolutions, or return columns change.

------------------------------------------------------------------------

## License

Add your chosen license and its terms before distributing this project
publicly.
