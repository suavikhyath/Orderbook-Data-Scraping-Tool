# Delta API – Additional Testing Findings

## 1. Overview

This document records additional offline tests conducted for the Delta API integration in the Orderbook Data Scraping Tool.

The objective was to identify gaps in the existing test coverage, particularly around API failures, invalid responses, empty data and candle interval handling.

## 2. Test Coverage

The following areas were tested:

| Area | Test coverage |
|---|---|
| Successful API calls | Checks successful responses |
| HTTP errors | Tests 400, 401, 403, 422, 429, 500, 502, 503 and 504 status codes |
| API errors | Checks API-level errors returned in JSON |
| Network failures | Tests timeout and connection errors |
| Malformed responses | Tests invalid JSON responses |
| Empty responses | Checks empty candle and product responses |
| Missing fields | Tests missing result, timestamp and candle fields |
| Invalid data | Tests invalid candle values and timestamps |
| Pagination | Checks pagination and repeated cursors |
| Candle intervals | Checks custom, zero and negative hour intervals |

## 3. Testing Approach

- Used `unittest` and `unittest.mock`.
- Used mocked HTTP responses to test API behaviour without depending on live API availability.
- Used temporary directories for file-related tests.
- Used assertions to verify expected results and exceptions.

## 4. Findings and Limitations

1. HTTP errors are propagated through `raise_for_status()`.
2. API-level errors are handled when the response contains `success: false`.
3. Empty candle responses return an empty DataFrame.
4. Missing required candle fields raise a `ValueError`.
5. Invalid timestamps and numeric candle values are converted or removed during data cleaning.
6. Repeated pagination cursors are detected.
7. Zero and negative candle intervals are currently accepted by the function. There is no explicit validation rejecting them.

**Testing limitation:** Some tests, such as the duplicate-candle and OHLC relationship checks, operate directly on sample DataFrames rather than testing the complete production `fetch_candles()` function.

## 5. Files Involved

- `src/delta_vault/delta_api.py` – Existing Delta API implementation.
- `src/api_tests/delta_api_test.py` – Delta API test cases.
- `docs/deltaapi_extratests_findings.md` – Additional testing findings.

## 6. Running the Tests

From the project root:

```powershell
python -m pytest src/api_tests/delta_api_test.py -v
```

To display print statements:

```powershell
python -m pytest src/api_tests/delta_api_test.py -v -s
```

## 7. Conclusion

Additional offline tests were introduced to improve coverage of API failures, malformed responses, missing data, pagination and candle interval handling.

The testing also identified areas for potential improvement, particularly explicit validation of candle intervals and stronger integration-level testing of candle data processing.

No production API implementation changes were made as part of this testing work.