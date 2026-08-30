# Functions for finding the most common trends in the past few days (default: as of twoday, past 3 days)
from datetime import date, timedelta


def rank_trends(conn, as_of=None, window_days=3):
    """
    Rank trends based on the number of articles in the past `window_days` days.
    Returns a list of tuples (trend, count) sorted by count in descending order.
    """
    if as_of is None:
        as_of = date.today()
    if isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)
    start_date = as_of - timedelta(days=window_days - 1)  # Includes today in the window
    as_of = as_of.isoformat()
    start_date = start_date.isoformat()
     
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ac.cluster_label, COUNT(*) as count
        FROM article_clusters ac
        JOIN fact_news fn ON fn.id = ac.article_id
        JOIN dim_date dd ON fn.date_id = dd.date_id
        WHERE dd.date >= ? AND dd.date <= ? AND ac.cluster_label != -1
        GROUP BY ac.cluster_label
        ORDER BY count DESC
    """, (start_date, as_of))
    
    return cursor.fetchall()