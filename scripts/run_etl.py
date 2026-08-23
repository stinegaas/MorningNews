#!/usr/bin/env python
"""Entry point for a single ETL run.

Meant to run after fetch_news.py — reads every raw batch file in data/raw/,
cleans each article, and loads it into the star schema database. Safe to run
repeatedly / over overlapping raw files: loading is idempotent (see
newsintel.etl.load) and schema creation is CREATE TABLE IF NOT EXISTS.

Run with:  python scripts/run_etl.py
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newsintel.etl.clean import clean_article
from newsintel.etl.load import load_article
from newsintel.etl.schema import create_schema, get_connection
from newsintel.ingestion.fetch import load_sources

RAW_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "warehouse.db"


def read_raw_articles(raw_dir: Path) -> list[dict]:
    articles = []
    for path in sorted(raw_dir.glob("*.jsonl")):
        with open(path, "r", encoding="utf-8") as f:
            articles.extend(json.loads(line) for line in f)
    return articles


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # name -> feed url, so get_or_create_source() has something to store in dim_source.url
    source_urls = {source["name"]: source["url"] for source in load_sources()}

    conn = get_connection(str(DB_PATH))
    create_schema(conn)

    raw_articles = read_raw_articles(RAW_DATA_DIR)
    logging.info("Read %d raw articles from %s", len(raw_articles), RAW_DATA_DIR)

    for raw in raw_articles:
        cleaned = clean_article(raw)
        source_url = source_urls.get(cleaned["source"], "")
        if not source_url:
            logging.warning("No URL in sources.yaml for source %r", cleaned["source"])
        load_article(conn, cleaned, source_url)

    n_fact = conn.execute("SELECT COUNT(*) FROM fact_news").fetchone()[0]
    conn.close()

    logging.info("Loaded %d raw articles; fact_news now has %d rows total", len(raw_articles), n_fact)


if __name__ == "__main__":
    main()
