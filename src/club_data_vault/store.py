from __future__ import annotations

import json
from pathlib import Path

from huggingface_hub import HfApi, get_token, hf_hub_download
from huggingface_hub.errors import EntryNotFoundError

from .config import settings


class DatasetStore:
    """Read-only Hugging Face Dataset access; the token is never logged."""

    def __init__(self, repo_id: str | None = None):
        self.repo_id = repo_id or settings.dataset_repo
        self.token = settings.hf_token or get_token()
        self.api = HfApi(token=self.token)

    def list_files(self) -> list[str]:
        return list(self.api.list_repo_files(self.repo_id, repo_type="dataset"))

    def download(self, path: str) -> str:
        return hf_hub_download(
            repo_id=self.repo_id,
            repo_type="dataset",
            filename=path,
            token=self.token,
        )

    def catalog(self) -> list[dict]:
        try:
            manifest = json.loads(Path(self.download("manifest.json")).read_text())
            return manifest.get("instruments", [])
        except EntryNotFoundError:
            return self._discover_catalog()

    def _discover_catalog(self) -> list[dict]:
        grouped: dict[str, dict] = {}
        for path in self.list_files():
            parts = path.split("/")
            if len(parts) == 3 and parts[0] == "Binance" and path.endswith(".parquet"):
                symbol = Path(parts[-1]).stem.upper()
                grouped[f"binance:{symbol}"] = {
                    "instrument_id": f"binance:{symbol}",
                    "exchange": "binance",
                    "symbol": symbol,
                    "intervals": ["1h"],
                    "paths": [path],
                }
            elif len(parts) == 4 and parts[0] == "Delta_Exchange" and path.endswith(".parquet"):
                symbol = parts[2].upper()
                item = grouped.setdefault(
                    f"delta:{symbol}",
                    {
                        "instrument_id": f"delta:{symbol}",
                        "exchange": "delta",
                        "symbol": symbol,
                        "intervals": ["1m"],
                        "paths": [],
                    },
                )
                item["paths"].append(path)
        for item in grouped.values():
            item["paths"].sort()
        return sorted(grouped.values(), key=lambda item: item["instrument_id"])
