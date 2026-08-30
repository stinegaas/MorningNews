""" 
Uses a pretrained model to embed title + summary text -> later steps 
(clustering, trend detection) can work with semantic similarity instead of raw text.

Stored in its own table, not as a column on fact_news: embeddings are a
derived artifact of a specific model, not raw warehouse data. This way
they can be regenerated without touching the star schema, and
sit alongside a future, separate TF-IDF representation without collision.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


def create_embeddings_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS article_embeddings (
            article_id INTEGER PRIMARY KEY REFERENCES fact_news(id),
            model_name TEXT NOT NULL,
            embedding BLOB NOT NULL
        );
        """
    )
    conn.commit()


def combine_text(title: str, summary: Optional[str]) -> str:
    """Text fed to the embedding model. Falls back to title alone when summary
    is missing. Whether these articles should be treated differently downstream
    (e.g. weighted less in clustering) is a separate, deliberately deferred
    decision -- this is just what goes into the model today."""
    if summary:
        return f"{title} {summary}"
    return title


# Recurring feed segments, not actual news stories -- excluded from embedding
# (and therefore from clustering/trends/summarization downstream) rather than
# from fact_news at ETL time, per this project's existing rule that content
# filtering is a feature-engineering decision, not a data-warehouse one.
# Found via a real cluster the LLM correctly refused to summarize ("generic
# news bulletin headers without any actual article content") -- all 22 came
# from a single source, Euronews' recurring "Latest news bulletin | <date>
# <time>" segment marker.
EXCLUDED_TITLE_PATTERNS = ["Latest news bulletin |%"]


def get_unembedded_articles(conn: sqlite3.Connection) -> list[tuple[int, str, Optional[str]]]:
    """Articles in fact_news with no row in article_embeddings yet. Makes
    re-running this script incremental."""
    exclude_clause = " AND ".join("f.title NOT LIKE ?" for _ in EXCLUDED_TITLE_PATTERNS)
    return conn.execute(
        f"""
        SELECT f.id, f.title, f.summary
        FROM fact_news f
        LEFT JOIN article_embeddings e ON e.article_id = f.id
        WHERE e.article_id IS NULL
        AND {exclude_clause}
        """,
        EXCLUDED_TITLE_PATTERNS,
    ).fetchall()


def compute_embeddings(model: SentenceTransformer, texts: list[str]) -> np.ndarray:
    return model.encode(texts, show_progress_bar=False, convert_to_numpy=True)


def save_embeddings(
    conn: sqlite3.Connection,
    article_ids: list[int],
    embeddings: np.ndarray,
    model_name: str = MODEL_NAME,
) -> None:
    conn.executemany(
        "INSERT OR REPLACE INTO article_embeddings (article_id, model_name, embedding) VALUES (?, ?, ?)",
        [
            (article_id, model_name, embedding.astype(np.float32).tobytes())
            for article_id, embedding in zip(article_ids, embeddings)
        ],
    )
    conn.commit()


def load_embedding(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32).copy()
