"""Compute TF-IDF vectors for articles.

TF-IDF is not persisted, unlike embeddings. Has to be fit on everything all at once. 

Uses the same combine_text() as embeddings.py, so both representations see
identical input text. Needed for a fair comparison.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

import scipy.sparse
from sklearn.feature_extraction.text import TfidfVectorizer

from newsintel.features.embeddings import combine_text


def get_all_articles(conn: sqlite3.Connection) -> list[tuple[int, str, Optional[str]]]:
    return conn.execute("SELECT id, title, summary FROM fact_news").fetchall()


def compute_tfidf(texts: list[str]) -> tuple[scipy.sparse.csr_matrix, TfidfVectorizer]:
    """Returns the sparse matrix (one row per text) and the fitted vectorizer 
    (needed later to inspect vocabulary/feature names for interpretability (the whole point of using TF-IDF)."""
    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform(texts)
    return matrix, vectorizer
