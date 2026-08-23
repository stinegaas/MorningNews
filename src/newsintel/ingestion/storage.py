"""Persist raw fetched articles to disk, one newline-delimited JSON file per run.

Kept separate from fetch.py: fetching and persisting are different
responsibilities, and it lets fetch_all() be tested without touching disk.

  - Skriver artiklene som JSON Lines (én JSON-linje per artikkel) til data/raw/, med filnavn = tidspunkt for
    kjøringen. Hver batch-kjøring blir dermed sin egen fil — du får en full historikk av rå-hentinger, og
    ETL-steget ditt kan senere velge å lese én fil, flere, eller alle.
  - Dette er "rålaget" — helt ubehandlet, rett fra RSS. Rensing/strukturering til star schema er bevisst IKKE
    gjort her, det er jobben til ETL-modulen du skal bygge selv.

"""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .fetch import RawArticle

RAW_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"


def save_raw_articles(articles: list[RawArticle], output_dir: Path = RAW_DATA_DIR) -> Path:
    """Write articles as JSONL to a timestamped file, one file per run.

    Raw data is intentionally kept as-is here (no cleaning/deduping) — that's
    the ETL step's job, working off these files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"{timestamp}.jsonl"

    with open(output_path, "w", encoding="utf-8") as f:
        for article in articles:
            f.write(json.dumps(asdict(article), ensure_ascii=False) + "\n")

    return output_path
