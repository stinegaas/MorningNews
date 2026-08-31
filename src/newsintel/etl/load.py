"""Load cleaned articles into the star schema. Safe to call repeatedly with overlapping data (e.g. across batch runs).
dim_source/dim_date rows are reused via get-or-create, and fact_news rows are skipped if the same link is already loaded.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime


def get_or_create_source(conn: sqlite3.Connection, name: str, url: str) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO dim_source (name, url) VALUES (?, ?)",
        (name, url),
    )
    row = conn.execute("SELECT source_id FROM dim_source WHERE name = ?", (name,)).fetchone()
    return row[0]


def get_or_create_date(conn: sqlite3.Connection, date_str: str) -> int:
    date = datetime.fromisoformat(date_str).date()
    date_iso = date.isoformat()

    conn.execute(
        "INSERT OR IGNORE INTO dim_date (date, year, month, day) VALUES (?, ?, ?, ?)",
        (date_iso, date.year, date.month, date.day),
    )
    row = conn.execute("SELECT date_id FROM dim_date WHERE date = ?", (date_iso,)).fetchone()
    return row[0]


def load_article(conn: sqlite3.Connection, article: dict, source_url: str) -> None:
    """Insert one cleaned article into fact_news."""
    source_id = get_or_create_source(conn, article["source"], source_url)

    date_str = article["published_parsed"] or article["fetched_at"]
    date_id = get_or_create_date(conn, date_str)

    conn.execute(
        """
        INSERT OR IGNORE INTO fact_news (link, title, summary, published, fetched_at, source_id, date_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            article["link"],
            article["title"],
            article["summary"],
            article["published_parsed"],
            article["fetched_at"],
            source_id,
            date_id,
        ),
    )
    conn.commit()
