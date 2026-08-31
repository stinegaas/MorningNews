"""Persist the final, chosen clustering result to the warehouse.

Saving always replaces the whole table rather than inserting only what´s missing. 
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
