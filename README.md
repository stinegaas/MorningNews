# Morning News

A personal data engineering/AI project: ingest international news via RSS, cluster related articles into stories, rank them by how much they're being discussed, and summarize each trending story with an LLM. The result is shown in a small Streamlit dashboard.

Built as a learning project focused on data + AI engineering: the clustering algorithm is built from scratch, evaluated empirically against multiple metrics before picking a configuration, and the pipeline runs on top of a star-schema data warehouse.

## Pipeline

```
RSS feeds (~15 international sources)
  -> fetch_news.py         raw ingestion (JSONL)
  -> run_etl.py            load into a star-schema SQLite warehouse
  -> run_embeddings.py     sentence embeddings per article (incremental)
  -> run_clustering.py     hand-built DBSCAN over article similarity -> "stories"
  -> run_summarization.py  LLM headline + summary per story (Claude Haiku 4.5)
  -> streamlit run app.py  dashboard: trending stories, ranked and summarized
```

Each step reads from the warehouse and writes back to it. The pipeline is re-run manually by Stine (see below), not on a schedule.


## Data warehouse

Star schema (SQLite): `fact_news` (articles) with `dim_source` and `dim_date`. Derived model artifacts — embeddings, cluster assignments, LLM summaries — live in their own tables (`article_embeddings`, `article_clusters`, `cluster_summaries`) rather than as columns on `fact_news`, so they can be regenerated or swapped (different model, different clustering config) without touching the warehouse itself.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

LLM summarization requires an Anthropic API key:

```bash
export ANTHROPIC_API_KEY="your-key"
```

## Running the pipeline

From the project root, in order (each step depends on the previous one having run):

```bash
python scripts/fetch_news.py
python scripts/run_etl.py
python scripts/run_embeddings.py
python scripts/run_clustering.py
python scripts/run_summarization.py   # needs ANTHROPIC_API_KEY
streamlit run src/newsintel/dashboard/app.py
```

Fetching is manual -> dashboard's time-window control is capped at 3 days for this reason (RSS feeds only retain a rolling window of recent items, so coverage further back isn't reliable without more frequent fetching).

## Project structure

```
config/sources.yaml              RSS source list
src/newsintel/
  ingestion/                     RSS fetching + raw storage
  etl/                           star schema, cleaning, loading
  features/                      embeddings + TF-IDF
  clustering/                    DBSCAN + persistence
  trends/                        trend ranking (cluster size within a time window)
  summarization/                 LLM story summaries
  dashboard/                     Streamlit app
scripts/                         one entry point per pipeline step
notebooks/                       clustering exploration + evaluation
```

## Clustering evaluation

Clustering was evaluated empirically rather than picking parameters on assertion: internal validation (silhouette score, Davies-Bouldin index) across a threshold/min_samples sweep, plus external validation (Adjusted Rand Index, Normalized Mutual Information) against a small hand-labeled subset of articles. See `notebooks/exploreClustering.py` and `notebooks/clustering_results.txt` for the full sweep and results.
