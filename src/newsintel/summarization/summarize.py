"""
LLM summarization at the story/cluster level. Uses Claude Haiku 4.5.
Persisted like article_clusters: own table, full delete+reinsert each run.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict

import anthropic
from pydantic import BaseModel

from newsintel.features.embeddings import combine_text

MODEL_NAME = "claude-haiku-4-5"

SYSTEM_PROMPT = (
    "You summarize clusters of news article headlines that all cover the same "
    "story. Given a list of article titles and summaries, produce a short "
    "headline (5-8 words) and a 2-3 sentence summary of what the story is "
    "about, both in English.\n\n"
    "Strict output rules:\n"
    "- Plain text only. No markdown, no quotes, no trailing punctuation on "
    "the headline, no bullet points, no bold.\n"
    "- Do not mention that you were given multiple articles -- just describe "
    "the story itself."
)


class ClusterSummary(BaseModel):
    headline: str
    summary: str


def create_summaries_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cluster_summaries (
            cluster_label INTEGER PRIMARY KEY,
            threshold REAL NOT NULL,
            min_samples INTEGER NOT NULL,
            headline TEXT NOT NULL,
            summary TEXT NOT NULL,
            model_name TEXT NOT NULL
        );
        """
    )
    conn.commit()


def get_cluster_articles(conn: sqlite3.Connection) -> dict[int, list[tuple[str, str | None]]]:
    """Groups (title, summary) pairs by cluster_label, for every article in a real cluster."""
    rows = conn.execute(
        """
        SELECT ac.cluster_label, f.title, f.summary
        FROM article_clusters ac
        JOIN fact_news f ON f.id = ac.article_id
        WHERE ac.cluster_label != -1
        """
    ).fetchall()

    clusters: dict[int, list[tuple[str, str | None]]] = defaultdict(list)
    for cluster_label, title, summary in rows:
        clusters[cluster_label].append((title, summary))
    return clusters


def build_prompt(articles: list[tuple[str, str | None]]) -> str:
    lines = [combine_text(title, summary) for title, summary in articles] # combine title+summary like embeddings do, so the LLM sees the sametitle+summary text as the embeddings/TF-IDF representations
    return "\n".join(f"- {line}" for line in lines)


def summarize_cluster(client: anthropic.Anthropic, articles: list[tuple[str, str | None]]) -> tuple[str, str]:
    """Returns (headline, summary). Uses structured outputs (Pydantic schema
    via messages.parse)"""
    response = client.messages.parse(
        model=MODEL_NAME,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_prompt(articles)}],
        output_format=ClusterSummary,
    )
    result = response.parsed_output
    return result.headline.strip(), result.summary.strip()


def save_summaries(
    conn: sqlite3.Connection,
    summaries: dict[int, tuple[str, str]],
    threshold: float,
    min_samples: int,
) -> None:
    conn.execute("DELETE FROM cluster_summaries")
    conn.executemany(
        """
        INSERT INTO cluster_summaries (cluster_label, threshold, min_samples, headline, summary, model_name)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (cluster_label, threshold, min_samples, headline, summary, MODEL_NAME)
            for cluster_label, (headline, summary) in summaries.items()
        ],
    )
    conn.commit()
