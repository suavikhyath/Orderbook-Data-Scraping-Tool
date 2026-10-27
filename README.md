# Club Data Vault

A modular market-data infrastructure project for retrieving, processing, and eventually storing historical market data from multiple exchanges through a unified interface.

## Current Progress

- [x] Delta Exchange API integration
- [x] Upstox API integration
- [x] Historical OHLCV candle retrieval
- [x] Environment-based credential loading using `.env`
- [ ] Automatic Upstox instrument lookup
- [ ] Unified schema and normalization layer
- [ ] Comprehensive offline unit-test coverage
- [ ] Data validation and quality checks
- [ ] Persistent storage and incremental updates
- [ ] Unified ingestion interface

*Checklist items reflect the current development status and should be updated as features are completed and reviewed.*

## Current Architecture

```text
Club Data Vault
│
├── src/
│   ├── api_tests/
│   │   ├── indian_api_test.py
│   │   └── delta_api_test.py
│   │
│   └── delta_vault/
│       └── upstox/
│           └── upstox_api.py
│
├── samples/
├── docs/
├── tests/
├── .env
├── .gitignore
└── README.md
```

*This is a provisional overview of the structure established so far. Update it to match the repository's actual directories and files.*

## Supported Data Sources

### 1. Upstox

The current Upstox integration retrieves historical candle data using the Upstox Historical Candle API.

**Current capabilities**
- Authenticated API requests using an access token.
- Historical candle retrieval for a specified instrument and date range.
- Conversion of API responses into a Pandas DataFrame.
- Timestamp conversion and chronological sorting.

The current implementation accepts an Upstox instrument key directly. Automatic instrument discovery is planned.

### 2. Delta Exchange

The Delta Exchange integration provides the second market-data source.

Its existing implementation and tests should be reviewed before extending functionality. The next development phase will focus on aligning its output with the Upstox data format.

## Technology Stack

- **Language:** Python
- **HTTP client:** Requests
- **Data processing:** Pandas
- **Configuration:** `python-dotenv`
- **Testing:** Pytest
- **Version control:** Git and GitHub

## Setup

### Prerequisites

- Python 3.10 or newer
- Git
- API credentials for the providers being tested live

### Installation

Clone the repository and enter its directory:

```bash
git clone <repository-url>
cd club-data-vault
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the current dependencies:

```bash
pip install requests pandas python-dotenv pytest
```

If the project has a `requirements.txt` or `pyproject.toml`, use the repository's declared dependencies instead.

### Environment Configuration

Create a `.env` file in the appropriate project root:

```env
UPSTOX_API_KEY=your_api_key
UPSTOX_API_SECRET=your_api_secret
UPSTOX_ACCESS_TOKEN=your_access_token
```

Keep real credentials private. Never commit `.env` or API tokens to version control.

## Running the Upstox Integration

The current historical-candle function accepts an instrument key, timeframe, and date range.

Example:

```python
df = get_candles(
    instrument_key="NSE_EQ|INE002A01018",
    timeframe="days",
    from_date="2026-01-01",
    to_date="2026-10-26",
)

print(df.head())
```

The function returns a Pandas DataFrame containing:

| Column | Description |
|---|---|
| `timestamp` | Candle timestamp |
| `open` | Opening price |
| `high` | Highest price |
| `low` | Lowest price |
| `close` | Closing price |
| `volume` | Traded volume |
| `open_interest` | Open interest, where applicable |

The example uses a daily interval. Supported intervals and historical-data limits depend on the Upstox API.

## Testing

Run the existing tests using the repository's configured test paths:

```bash
pytest -v
```

Tests should progressively cover:

- Successful API responses
- Empty responses
- HTTP errors and timeouts
- Malformed response structures
- Timestamp ordering and data types
- Provider-specific edge cases

Offline unit tests should use mocked HTTP responses so that normal test runs do not depend on internet access or valid API credentials.

## Planned Development

### Phase 1 — Instrument Discovery and Test Coverage
- Implement Upstox instrument lookup using official instrument master data.
- Audit existing provider tests and add only missing coverage.

### Phase 2 — Unified Data Model
- Define a common OHLCV schema.
- Standardize timestamp conventions, identifiers, numeric types, and provider metadata.
- Normalize both providers' responses.

### Phase 3 — Data Quality
- Detect duplicate candles, missing fields, invalid prices, and inconsistent timestamps.
- Establish validation rules and automated tests.

### Phase 4 — Storage
- Evaluate CSV and Parquet against expected data volume and access patterns.
- Implement persistent storage and incremental updates.
- Prevent duplicate records during repeated ingestion.

### Phase 5 — Unified Ingestion
- Provide a common interface for retrieving data from supported providers.
- Add logging, retries, rate-limit handling, and end-to-end tests.

## Contribution Guidelines

1. Create a separate branch for each task.
2. Keep provider-specific code separate from shared processing logic.
3. Write tests for new functionality.
4. Open a pull request for review before merging into `main`.
5. Never commit credentials, tokens, or private configuration files.
6. Update documentation when interfaces or project behavior change.

## Project Status

**Current milestone:** Provider API integrations.

The immediate objective is to transform the existing exchange-specific implementations into a consistent, testable data pipeline. Persistent storage, normalization, and automated ingestion remain future milestones until implemented and verified.
