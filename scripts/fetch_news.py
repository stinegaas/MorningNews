#!/usr/bin/env python
"""Entry point for a single batch ingestion run.

Meant to be invoked periodically (e.g. via cron) — each run fetches all
configured RSS sources once and writes the results to data/raw/.

Run with:  python scripts/fetch_news.py
(from the project root, with src/ on PYTHONPATH — see the sys.path line below;
this is a lightweight stand-in for proper packaging, which isn't needed yet)

dette er inngangspunktet en cron-jobb vil kalle for å utføre én
  batch-henting. Binder sammen fetch_all() og save_raw_articles(), og setter opp logging så du ser hva som
  skjedde (hvor mange artikler per kilde, hvilke kilder feilet).
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newsintel.ingestion.fetch import fetch_all
from newsintel.ingestion.storage import save_raw_articles


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    articles = fetch_all()
    output_path = save_raw_articles(articles)
    logging.info("Saved %d articles to %s", len(articles), output_path)


if __name__ == "__main__":
    main()
