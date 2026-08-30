#!/usr/bin/env python
"""Entry point for generating LLM summaries of each clustered story.

Requires ANTHROPIC_API_KEY to be set (or an `ant auth login` profile).

Run with:  python scripts/run_summarization.py
Depends on article_clusters already being populated -- run
scripts/run_clustering.py first. THRESHOLD/MIN_SAMPLES here must match what
run_clustering.py actually persisted, since cluster_label only means
something relative to that specific config.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import anthropic

from newsintel.etl.schema import get_connection
from newsintel.summarization.summarize import (
    create_summaries_table,
    get_cluster_articles,
    save_summaries,
    summarize_cluster,
)

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "warehouse.db"

THRESHOLD = 0.6
MIN_SAMPLES = 1


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    conn = get_connection(str(DB_PATH))
    create_summaries_table(conn)

    clusters = get_cluster_articles(conn)
    logging.info("Summarizing %d clusters", len(clusters))

    client = anthropic.Anthropic()
    summaries = {}
    for cluster_label, articles in clusters.items():
        try:
            summaries[cluster_label] = summarize_cluster(client, articles)
        except anthropic.APIError as e:
            logging.warning("Cluster %d failed, skipping: %s", cluster_label, e)

    save_summaries(conn, summaries, THRESHOLD, MIN_SAMPLES)
    logging.info("Saved %d/%d summaries to cluster_summaries", len(summaries), len(clusters))


if __name__ == "__main__":
    main()
