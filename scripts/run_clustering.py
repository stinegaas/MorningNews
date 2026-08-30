#!/usr/bin/env python
"""Entry point for running the final, chosen clustering configuration and
persisting the result.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newsintel.clustering.dbscan import load_similarity_matrix, dbscan
from newsintel.clustering.persist import create_clusters_table, save_clusters
from newsintel.etl.schema import get_connection

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "warehouse.db"

THRESHOLD = 0.6
MIN_SAMPLES = 1


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    conn = get_connection(str(DB_PATH))
    create_clusters_table(conn)

    article_ids, sim = load_similarity_matrix(conn)
    logging.info("Clustering %d articles (threshold=%s, min_samples=%s)", len(article_ids), THRESHOLD, MIN_SAMPLES)

    labels = dbscan(sim, threshold=THRESHOLD, min_samples=MIN_SAMPLES)
    n_clusters = len(set(labels) - {-1})
    n_noise = labels.count(-1)
    logging.info("%d clusters, %d noise", n_clusters, n_noise)

    save_clusters(conn, article_ids, labels, THRESHOLD, MIN_SAMPLES)
    logging.info("Saved to article_clusters")


if __name__ == "__main__":
    main()
