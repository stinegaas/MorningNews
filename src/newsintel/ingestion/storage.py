"""Persist raw fetched articles to disk, one newline-delimited JSON file per run.
  - Writes articles as JSON Lines (one JSON line per article) to data/raw/, with the filename set to
    the run's timestamp. Each batch run therefore gets its own file. You get a full history of raw
    fetches, and the ETL step can later choose to read one file, several, or all of them.
  - This is the raw layer. Unprocessed, straight from RSS.
"""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .fetch import RawArticle

RAW_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"


def save_raw_articles(articles: list[RawArticle], output_dir: Path = RAW_DATA_DIR) -> Path:
    """Write articles as JSONL to a timestamped file, one file per run."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"{timestamp}.jsonl"

    with open(output_path, "w", encoding="utf-8") as f:
        for article in articles:
            f.write(json.dumps(asdict(article), ensure_ascii=False) + "\n")

    return output_path
