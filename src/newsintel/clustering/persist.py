"""Persist the final, chosen clustering result to the warehouse.

Deliberately Not one row per experimental run -- clustering was evaluated
empirically across many threshold/min_samples combinations (see
notebooks/exploreClustering.py), but only the winning configuration gets
written here. Own table, not a column on fact_news, same reasoning as
article_embeddings: this is a derived model artifact tied to a specific
config, not raw warehouse data.

Unlike embeddings (incremental, one article at a time), clustering is a
global computation over the whole similarity matrix -- every article's label
can change when the algorithm re-runs. So saving always replaces the whole
table rather than inserting only what's missing.
"""

from __future__ import annotations

import sqlite3


def create_clusters_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS article_clusters (
            article_id INTEGER PRIMARY KEY REFERENCES fact_news(id),
            cluster_label INTEGER NOT NULL,
            threshold REAL NOT NULL,
            min_samples INTEGER NOT NULL
        );
        """
    )
    conn.commit()


""" Global computation -> old table is wiped and replaced """
def save_clusters(
    conn: sqlite3.Connection,
    article_ids: list[int],
    labels: list[int],
    threshold: float,
    min_samples: int,
) -> None:
    """Replaces the entire table -- see module docstring for why this isn't
    incremental. cluster_label of -1 (noise) is stored too: "not part of any
    story" is meaningful information for downstream steps (trend ranking,
    dashboard), not something to silently drop."""
    conn.execute("DELETE FROM article_clusters")
    conn.executemany(
        """
        INSERT INTO article_clusters (article_id, cluster_label, threshold, min_samples)
        VALUES (?, ?, ?, ?)
        """,
        [
            (article_id, label, threshold, min_samples)
            for article_id, label in zip(article_ids, labels)
        ],
    )
    conn.commit()
