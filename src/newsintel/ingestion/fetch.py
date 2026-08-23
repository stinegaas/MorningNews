"""Fetch and parse news articles from the RSS feeds listed in config/sources.yaml."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import feedparser
import requests
import yaml

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "sources.yaml"
REQUEST_TIMEOUT_SECONDS = 10


@dataclass
class RawArticle:
    """One article exactly as it came off the RSS feed, before any ETL cleaning."""

    source: str
    title: str
    link: str
    published: Optional[str]
    """Raw, unparsed date string exactly as the feed wrote it (format varies by source)."""
    published_parsed: Optional[str]
    """published, normalized to an ISO 8601 UTC string by feedparser's own date parsing.
    None if the entry had no parseable date. Use this one for anything that needs a
    real datetime (e.g. dim_dato) — don't re-parse `published` yourself."""
    summary: Optional[str]
    fetched_at: str


def _parsed_struct_to_iso(struct: Optional[time.struct_time]) -> Optional[str]:
    """Convert feedparser's *_parsed (a UTC time.struct_time) to an ISO 8601 string."""
    if struct is None:
        return None
    return datetime(*struct[:6], tzinfo=timezone.utc).isoformat()


def load_sources(config_path: Path = CONFIG_PATH) -> list[dict]:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("sources", [])


def fetch_source(source: dict) -> list[RawArticle]:
    """Fetch and parse a single RSS feed.

    Feed parsing errors are logged, not raised, so a malformed feed doesn't
    take down the whole batch run in fetch_all(). Fetching goes through
    requests (not feedparser's own URL handling) so we get an explicit,
    short timeout — feedparser.parse(url) otherwise falls back to the OS
    socket default, which can leave one slow/hanging source stalling the
    whole batch for a long time (observed ~44s against a timed-out feed
    during testing).
    """
    name = source["name"]
    url = source["url"]
    fetched_at = datetime.now(timezone.utc).isoformat()

    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    parsed = feedparser.parse(response.content)
    if parsed.bozo:
        logger.warning("Feed %s (%s) parsed with warnings: %s", name, url, parsed.bozo_exception)

    return [
        RawArticle(
            source=name,
            title=entry.get("title", "").strip(),
            link=entry.get("link", ""),
            published=entry.get("published"),
            published_parsed=_parsed_struct_to_iso(entry.get("published_parsed")),
            summary=entry.get("summary"),
            fetched_at=fetched_at,
        )
        for entry in parsed.entries
    ]


def fetch_all(sources: Optional[list[dict]] = None) -> list[RawArticle]:
    """Fetch every configured source. A failing source is logged and skipped,
    not allowed to abort the whole run."""
    if sources is None:
        sources = load_sources()

    all_articles: list[RawArticle] = []
    for source in sources:
        try:
            articles = fetch_source(source)
            logger.info("Fetched %d articles from %s", len(articles), source["name"])
            all_articles.extend(articles)
        except Exception:
            logger.exception("Failed to fetch source %s", source.get("name", "?"))

    return all_articles
