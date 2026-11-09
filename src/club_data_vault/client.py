from __future__ import annotations

from datetime import date
import re

import pandas as pd

from .store import DatasetStore


def _date(value: date | str | None) -> date | None:
    if isinstance(value, str):
        return date.fromisoformat(value)
    return value


def _interval(path: str, item: dict) -> str:
    if path.startswith("data/binance/spot/"):
        return "1d"
    if path.startswith("Binance/"):
        return "1h"
    if path.startswith("upstox/data/1hr/"):
        return "1h"
    if path.startswith("upstox/data/1m/"):
        return "1m"
    return (item.get("intervals") or [""])[0]


def _seconds(value: str) -> int:
    match = re.fullmatch(r"(\d+)(m|h|d|w)", value.lower())
    if not match:
        raise ValueError("interval must look like 1m, 5m, 1h, 1d, or 1w")
    amount, unit = int(match.group(1)), match.group(2)
    return amount * {"m": 60, "h": 3600, "d": 86400, "w": 604800}[unit]


def _pandas_frequency(value: str) -> str:
    match = re.fullmatch(r"(\d+)(m|h|d|w)", value.lower())
    if not match:
        raise ValueError("interval must look like 1m, 5m, 1h, 1d, or 1w")
    amount, unit = int(match.group(1)), match.group(2)
    return f"{amount}{ {'m': 'min', 'h': 'h', 'd': 'D', 'w': 'W'}[unit] }"


def _normalize(frame: pd.DataFrame, item: dict, interval: str) -> pd.DataFrame:
    frame = frame.copy()
    if "timestamp" not in frame and "open_time" in frame:
        frame["timestamp"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
    else:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["exchange"] = item.get("exchange", "")
    frame["symbol"] = item.get("symbol", frame.get("symbol", ""))
    frame["interval"] = interval
    return frame


def _resample(frame: pd.DataFrame, interval: str) -> pd.DataFrame:
    if frame.empty:
        return frame
    frame = frame.set_index("timestamp")
    aggregations = {
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum",
    }
    available = {key: value for key, value in aggregations.items() if key in frame.columns}
    result = frame.resample(_pandas_frequency(interval), label="left", closed="left").agg(available)
    result = result.dropna(subset=[key for key in ("open", "high", "low", "close") if key in result])
    result["timestamp"] = result.index
    result["interval"] = interval
    return result.reset_index(drop=True)


class DataClient:
    def __init__(self, store: DatasetStore | None = None):
        self.store = store or DatasetStore()

    def catalog(self) -> list[dict]:
        return self.store.catalog()

    def load(
        self,
        *,
        instrument: str | None = None,
        exchange: str | None = None,
        symbol: str | None = None,
        interval: str | None = None,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
    ) -> pd.DataFrame:
        start_date = _date(start_date)
        end_date = _date(end_date)
        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date must not be after end_date")
        items = self.catalog()
        if instrument:
            items = [item for item in items if item.get("instrument_id") == instrument]
        if exchange:
            items = [item for item in items if item.get("exchange") == exchange]
        if symbol:
            items = [item for item in items if item.get("symbol", "").upper() == symbol.upper()]
        if interval:
            requested_seconds = _seconds(interval)
            items = [
                item for item in items
                if any(_seconds(source) <= requested_seconds and requested_seconds % _seconds(source) == 0 for source in item.get("intervals", []))
            ]
        if len(items) != 1:
            raise ValueError("Filters must identify exactly one instrument")

        item = items[0]
        paths = item.get("paths", []) or ([item["path"]] if item.get("path") else [])
        available = [(path, _interval(path, item)) for path in paths]
        if interval:
            requested_seconds = _seconds(interval)
            usable = [
                (path, source) for path, source in available
                if _seconds(source) <= requested_seconds and requested_seconds % _seconds(source) == 0
            ]
            if not usable:
                raise ValueError(f"No source data can provide requested interval {interval}")
            finest_usable = max(_seconds(source) for _, source in usable)
            available = [(path, source) for path, source in usable if _seconds(source) == finest_usable]
        else:
            source_intervals = {source for _, source in available}
            if len(source_intervals) != 1:
                raise ValueError("interval is required when an instrument has multiple intervals")
        paths = available
        if not paths:
            raise FileNotFoundError("No data files match the requested filters")

        frames = [
            _normalize(pd.read_parquet(self.store.download(path)), item, source)
            for path, source in paths
        ]
        frame = pd.concat(frames, ignore_index=True)
        frame = frame.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
        if start_date:
            frame = frame[frame["timestamp"].dt.date >= start_date]
        if end_date:
            frame = frame[frame["timestamp"].dt.date <= end_date]
        requested_interval = interval or paths[0][1]
        source_interval = paths[0][1]
        if _seconds(requested_interval) > _seconds(source_interval):
            frame = _resample(frame, requested_interval)
        else:
            frame["interval"] = requested_interval
        return frame.reset_index(drop=True)


def load_data(**filters) -> pd.DataFrame:
    """Load one instrument as a Pandas DataFrame."""
    return DataClient().load(**filters)
