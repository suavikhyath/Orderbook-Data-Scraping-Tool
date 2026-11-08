
import os
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import HfApi


# Project root: data-vault/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Dataset directory: src/deltadataset/
BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data" / "crypto-top20-1m"
CONFIG_FILE = BASE_DIR / "config" / "coins.json"

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)

REPO_ID = os.getenv("HF_REPO_ID")


def main():

    if not REPO_ID:
        raise ValueError(
            "HF_REPO_ID missing in project-root .env"
        )

    if not DATA_DIR.exists():
        raise FileNotFoundError(DATA_DIR)

    files = list(DATA_DIR.rglob("*.parquet"))

    if not files:
        raise RuntimeError("No Parquet files found.")

    total_size = sum(
        f.stat().st_size for f in files
    )

    print("Repository:", REPO_ID)
    print("Parquet files:", len(files))
    print(f"Total size: {total_size / 1024**3:.2f} GB")

    api = HfApi()

    api.create_repo(
        repo_id=REPO_ID,
        repo_type="dataset",
        exist_ok=True,
    )

    print("\nUploading Parquet files...")

    api.upload_folder(
        repo_id=REPO_ID,
        repo_type="dataset",
        folder_path=str(DATA_DIR),
        path_in_repo="data",
        commit_message="Upload crypto top 20 1m Parquet data",
    )

    if CONFIG_FILE.exists():

        print("\nUploading coins.json...")

        api.upload_file(
            path_or_fileobj=str(CONFIG_FILE),
            path_in_repo="coins.json",
            repo_id=REPO_ID,
            repo_type="dataset",
            commit_message="Upload coin ranking configuration",
        )

    print("\nUpload completed!")
    print(
        f"https://huggingface.co/datasets/{REPO_ID}"
    )


if __name__ == "__main__":
    main()
