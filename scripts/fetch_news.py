#!/usr/bin/env python
"""Entry point for a single batch ingestion run. Each run fetches all
configured RSS sources once and writes the results to data/raw/.
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
