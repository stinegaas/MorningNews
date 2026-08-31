"""Streamlit dashboard: trending stories from the news warehouse.

Depends on the earlier pipeline steps already having run.

Run with:  streamlit run src/newsintel/dashboard/app.py
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plotly.graph_objects as go
import streamlit as st

from newsintel.etl.schema import get_connection
from newsintel.summarization.summarize import create_summaries_table
from newsintel.trends.trendRanking import rank_trends

DB_PATH = Path(__file__).resolve().parents[3] / "data" / "warehouse.db"
TOP_N = 15

st.set_page_config(page_title="Morning News", layout="wide")


@st.cache_resource
def get_conn():
    conn = get_connection(str(DB_PATH))
    create_summaries_table(conn)  # idempotent -- safe even if summarization hasn't run yet
    return conn


def get_data_max_date(conn) -> date:
    """Default for the as_of picker. The dataset is a static snapshot, not live-updating, so defaulting to real "today" would
    show an empty window until fetch_news.py runs again."""
    row = conn.execute("SELECT MAX(date) FROM dim_date").fetchone()
    return date.fromisoformat(row[0])


def get_cluster_details(conn, cluster_labels: list[int]) -> dict[int, dict]:
    """For each cluster_label: its LLM headline+summary (both None if not
    generated yet) and up to 3 example headlines, for display alongside the
    ranking."""
    if not cluster_labels:
        return {}

    placeholders = ",".join("?" * len(cluster_labels))

    llm_data = {
        cluster_label: {"headline": headline, "summary": summary}
        for cluster_label, headline, summary in conn.execute(
            f"SELECT cluster_label, headline, summary FROM cluster_summaries WHERE cluster_label IN ({placeholders})",
            cluster_labels,
        ).fetchall()
    }

    examples_by_cluster: dict[int, list[tuple[str, str]]] = {}
    rows = conn.execute(
        f"""
        SELECT ac.cluster_label, f.title, s.name
        FROM article_clusters ac
        JOIN fact_news f ON f.id = ac.article_id
        JOIN dim_source s ON f.source_id = s.source_id
        WHERE ac.cluster_label IN ({placeholders})
        """,
        cluster_labels,
    ).fetchall()
    for cluster_label, title, source_name in rows:
        examples_by_cluster.setdefault(cluster_label, []).append((title, source_name))

    return {
        cluster_label: {
            "headline": llm_data.get(cluster_label, {}).get("headline"),
            "summary": llm_data.get(cluster_label, {}).get("summary"),
            "examples": examples_by_cluster.get(cluster_label, [])[:3],
        }
        for cluster_label in cluster_labels
    }


def main():
    conn = get_conn()
    data_max_date = get_data_max_date(conn)

    # Always the latest date actually in the data, not user-selectable -- same
    # reasoning as capping window_days: fetching is manual and irregular, so
    # only the most recent snapshot is something the dashboard can stand
    # behind. An older as_of would show a fixed slice of history the user
    # has no way to know is complete or not.
    as_of = data_max_date

    st.title("Morning News -- Trending Stories")
    st.caption(f"Showing trends as of {as_of} (latest data available)")

    with st.sidebar:
        st.header("Settings")
        # Capped at 3 days: fetching happens manually, not on a reliable daily
        # schedule, so coverage beyond a few days back isn't guaranteed --
        # high-volume sources' RSS feeds roll over fast enough that a longer
        # window can silently under-represent them (see project notes). Not
        # letting the user pick a window we can't stand behind.
        window_days = st.select_slider("Time window (days)", options=[1, 2, 3], value=3)

    trends = rank_trends(conn, as_of=as_of, window_days=window_days)

    if not trends:
        window_start = as_of - timedelta(days=window_days - 1)
        st.warning(f"No articles found in the window {window_start} to {as_of}.")
        return

    top_trends = trends[:TOP_N]
    cluster_labels = [label for label, _ in top_trends]
    details = get_cluster_details(conn, cluster_labels)

    def label_for(cluster_label: int) -> str:
        headline = details.get(cluster_label, {}).get("headline")
        return headline if headline else f"Story {cluster_label}"

    fig = go.Figure(
        go.Bar(
            x=[count for _, count in top_trends],
            y=[label_for(label) for label, _ in top_trends],
            orientation="h",
        )
    )
    fig.update_layout(yaxis=dict(autorange="reversed"), title="Most discussed stories", height=100 + 30 * len(top_trends))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Details")
    for cluster_label, count in top_trends:
        info = details.get(cluster_label, {})
        summary = info.get("summary")
        header = f"{count} articles -- {label_for(cluster_label)}"
        with st.expander(header):
            if summary:
                st.write(summary)
            else:
                st.caption("No LLM summary generated yet for this story -- run scripts/run_summarization.py.")
            st.markdown("**Examples:**")
            for title, source_name in info.get("examples", []):
                st.markdown(f"- {title} *({source_name})*")


if __name__ == "__main__":
    main()
