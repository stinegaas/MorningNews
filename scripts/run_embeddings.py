#!/usr/bin/env python
"""Entry point for computing embeddings for articles that don't have them yet.

Run with:  python scripts/run_embeddings.py
Safe to re-run: only embeds articles missing from article_embeddings (see
get_unembedded_articles).
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentence_transformers import SentenceTransformer

from newsintel.etl.schema import get_connection
from newsintel.features.embeddings import (
    MODEL_NAME,
    combine_text,
    compute_embeddings,
    create_embeddings_table,
    get_unembedded_articles,
    save_embeddings,
)

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "warehouse.db"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    conn = get_connection(str(DB_PATH))
    create_embeddings_table(conn)

    articles = get_unembedded_articles(conn)
    logging.info("%d articles need embeddings", len(articles))
    if not articles:
        return

    article_ids = [row[0] for row in articles]
    texts = [combine_text(row[1], row[2]) for row in articles]

    logging.info("Loading model %s", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)

    embeddings = compute_embeddings(model, texts)
    save_embeddings(conn, article_ids, embeddings, MODEL_NAME)

    logging.info("Saved %d embeddings", len(article_ids))


if __name__ == "__main__":
    main()
