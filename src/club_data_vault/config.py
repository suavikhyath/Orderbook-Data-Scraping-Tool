from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    dataset_repo: str = os.getenv("HF_DATASET_REPO", "coepquantfinance/club-data-vault")
    hf_token: str | None = os.getenv("HF_TOKEN") or None


settings = Settings()
