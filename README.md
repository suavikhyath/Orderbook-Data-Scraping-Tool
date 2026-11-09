# Club Data Vault

A modular market-data platform for retrieving, processing, and serving historical market data from multiple exchanges.

The application code is stored in this GitHub repository. The actual market-data Parquet files are stored separately in the Hugging Face Dataset repository:

```text
coepquantfinance/club-data-vault
```

## Current Progress

- [x] Delta Exchange API integration
- [x] Upstox API integration
- [x] Historical OHLCV candle retrieval
- [x] Environment-based credential loading using `.env`
- [x] Hugging Face Dataset integration
- [x] Read-only Python client for club members
- [x] FastAPI market-data API
- [x] UTC timestamp normalization and duplicate removal
- [x] Interval-aware filtering and OHLCV resampling
- [ ] Automatic Upstox instrument lookup
- [ ] Corporate-action adjustment and complete gap reporting
- [ ] Hosted public API deployment

## Current Architecture

```text
Club Data Vault
│
├── src/
│   ├── api_tests/
│   ├── delta_vault/              # Earlier Delta and Upstox clients
│   └── club_data_vault/          # Shared client and FastAPI API
│       ├── api.py
│       ├── client.py
│       ├── config.py
│       └── store.py
│
├── tests/
├── docs/
├── pyproject.toml
├── requirements.txt
└── README.md
```

The `club_data_vault` package reads the existing Hugging Face Dataset repository without copying or modifying its data. The API and Python client use the same data-access layer.

## Supported Data Sources

### 1. Binance

The existing Dataset repository contains Binance Futures hourly Parquet files and Binance Spot daily data.

The client exposes the data using instrument identifiers such as:

```text
binance:BTCUSDT
```

### 2. Delta Exchange

The existing Dataset repository contains Delta Exchange monthly Parquet files with 1-minute candles.

Example instrument identifier:

```text
delta:BTCUSD
```

### 3. Upstox

The original Upstox integration retrieves historical candles using an instrument key directly. It remains available in `delta_vault/upstox/` but is not yet connected to the shared Hugging Face client catalog.

## Member Usage

Members can load data directly into Pandas without running a server:

```bash
python -m pip install git+https://github.com/suavikhyath/Orderbook-Data-Scraping-Tool.git
```

```python
from club_data_vault import load_data

df = load_data(
    instrument="delta:BTCUSD",
    interval="5m",
    start_date="2026-11-08",
    end_date="2026-11-08",
)
```

The client downloads only the required source Parquet files through `huggingface_hub`, filters the requested date range, normalizes timestamps to UTC, and returns a Pandas DataFrame.

If the requested interval is larger than the stored interval, the client resamples OHLCV data using:

- Open: first value
- High: maximum value
- Low: minimum value
- Close: last value
- Volume: sum

For example, Delta 1-minute data can serve a 5-minute request, and Binance hourly data can serve a daily request. Requests requiring finer data than available are rejected.

## FastAPI

Run the local API:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
export HF_DATASET_REPO=coepquantfinance/club-data-vault
uvicorn club_data_vault.api:app --reload
```

Open the interactive documentation at:

```text
http://127.0.0.1:8000/docs
```

Available endpoints:

```text
GET /health
GET /v1/exchanges
GET /v1/instruments
GET /v1/instruments/{instrument_id}
GET /v1/market-data
```

Example request:

```text
/v1/market-data?instrument=binance:BTCUSDT&interval=1d&start_date=2026-11-08&end_date=2026-11-08&format=parquet
```

The API can return JSON, CSV, or Parquet. It is currently intended to run locally or behind a separately chosen deployment service; the repository does not include a hosted server.

## Configuration and Authentication

The dataset is currently public, so downloads do not require a token. The repository can be made private later without changing the client design.

For private access, use either:

```env
HF_DATASET_REPO=coepquantfinance/club-data-vault
HF_TOKEN=your_token
```

or authenticate locally with:

```bash
hf auth login
```

Real tokens must never be committed or printed in logs.

## Technology Stack

- **Language:** Python
- **HTTP/API:** Requests and FastAPI
- **Data processing:** Pandas and PyArrow
- **Dataset access:** `huggingface_hub`
- **Storage format:** Parquet
- **Testing:** Pytest
- **Version control:** Git and GitHub

## Testing

Run the test suite:

```bash
pytest -q
```

The tests cover provider-independent loading, filtering, resampling, API health, and API data responses. The client and API have also been checked against the real Hugging Face Dataset repository.

## Data Layout

The reader supports the existing repository without migration:

```text
Binance/data/<SYMBOL>.parquet
Delta_Exchange/data/<SYMBOL>/<YYYY-MM>.parquet
manifest.json                    # used when available
```

If `manifest.json` is unavailable, the client discovers supported files from the repository tree through the Hugging Face API.

## Planned Development

- Connect Upstox instruments to the shared catalog.
- Add complete gap and data-quality reports.
- Add corporate-action handling where required.
- Add authentication and rate limiting if the API is deployed publicly.
- Add a hosted API only if the club needs a shared HTTP URL.

## Project Status

The read-only Python client and FastAPI API are working against the existing Hugging Face Dataset repository. The current branch focuses on reliable data access for research; automated refresh and hosted deployment are intentionally outside the current scope.
