# Testing how clustering works (with different min_samples, checking the clusters manually, evaluations) 

import sys, sqlite3
from collections import defaultdict
import numpy as np
sys.path.insert(0, "src")
from newsintel.clustering.dbscan import load_similarity_matrix, dbscan
from newsintel.features.embeddings import load_embedding
from sklearn.metrics import (
    adjusted_rand_score,
    normalized_mutual_info_score,
    silhouette_score,
    davies_bouldin_score,
)

conn = sqlite3.connect("data/warehouse.db")
ids, sim = load_similarity_matrix(conn)


def load_embeddings_matrix(conn, ids):
    """Embeddings in the same order as ids/sim, built via dict lookup."""
    rows = dict(conn.execute("SELECT article_id, embedding FROM article_embeddings").fetchall())
    return np.vstack([load_embedding(rows[article_id]) for article_id in ids])


embeddings = load_embeddings_matrix(conn, ids)

THRESHOLDS = [0.3, 0.4, 0.5, 0.6, 0.7]
MIN_SAMPLES_VALUES = [1, 2, 3, 5]

for threshold in THRESHOLDS:
    for min_samples in MIN_SAMPLES_VALUES:
        labels = dbscan(sim, threshold=threshold, min_samples=min_samples)
        n_clusters = len(set(labels) - {-1})
        n_noise = labels.count(-1)
        print(f"threshold={threshold}, min_samples={min_samples}: {n_clusters} clusters, {n_noise} noise")


def print_clusters(conn, ids, labels, min_size=2, show_noise=False):
    """Manual check: groups articles by cluster label and prints the titles,
    largest cluster first.
    """
    titles = dict(conn.execute("SELECT id, title FROM fact_news").fetchall())

    clusters = defaultdict(list)
    for article_id, label in zip(ids, labels):
        clusters[label].append(article_id)

    real_clusters = {cid: members for cid, members in clusters.items() if cid != -1}
    for cluster_id, members in sorted(real_clusters.items(), key=lambda kv: -len(kv[1])):
        if len(members) < min_size:
            continue
        print(f"\n--- cluster {cluster_id} ({len(members)} articles) ---")
        for article_id in members:
            print(" ", article_id, titles[article_id])

    if show_noise and -1 in clusters:
        noise = clusters[-1]
        print(f"\n--- noise (-1, {len(noise)} articles) ---")
        for article_id in noise:
            print(" ", article_id, titles[article_id])


# Example: manually check one specific configuration after looking at the
# numbers above. Change threshold/min_samples to the one you want to inspect.
# Commented out in the sweep below -- it prints all article titles and
# drowns out the evaluation tables. Turn it back on when you want to inspect one config.
#labels = dbscan(sim, threshold=0.6, min_samples=1)
#print_clusters(conn, ids, labels, show_noise=True)

true_labels = {
    # manually labeling clusters based on titles, used in external evaluation of DBSCAN. 

    # From partially incorrect cluster 3
    8: "World Humanoid Games",
    27: "World Humanoid Games",
    29: "World Humanoid Games",
    221: "World Humanoid Games",
    264: "World Humanoid Games",
    277: "World Humanoid Games",
    36: "Iran-sanksjoner",
    82: "Iran-sanksjoner",
    104: "Iran-sanksjoner",
    105: "Iran-sanksjoner",
    147: "Iran-sanksjoner",
    148: "Iran-sanksjoner",
    160: "Iran-sanksjoner",
    168: "Iran-sanksjoner",
    209: "Iran-sanksjoner",
    236: "Iran-sanksjoner",
    110: "Nord-Korea",
    260: "Nord-Korea",
    267: "Nord-Korea",
    268: "Nord-Korea",
    272: "AI",
    275: "AI",
    276: "AI",
    281: "AI",
    284: "AI",
    292: "AI",
    
    # From correct cluster 5
    10: "Israel-Palestina",
    17: "Israel-Palestina",
    45: "Israel-Palestina",
    269: "Israel-Palestina",
    311: "Israel-Palestina",
    459: "Israel-Palestina",
    502: "Israel-Palestina",

    # From outliers
    4: "Father leaves 7-year-old son alone on Mount Fuji to continue hike",
    5: "The hotel booking mix-up that could free mushroom murderer",
    6: "Dozens of co-ordinated arson attacks hit southern Thailand",
    7: "Trump Mobile promoted a 'Made in the USA' phone - but the details kept changing",
    12: "Fourteen killed in strike on Myanmar monastery",
    13: "US military newspaper editor voices censorship fears after being fired",
    14: "TikTok to pay $400m to US in one of largest child privacy settlements"
    }


def external_validation(ids, labels, true_labels):
    """ARI/NMI against true_labels for the articles that are hand-labeled."""
    pred_by_id = dict(zip(ids, labels))
    article_ids = list(true_labels.keys())

    y_true = [true_labels[aid] for aid in article_ids]
    y_pred = [pred_by_id[aid] for aid in article_ids]

    ari = adjusted_rand_score(y_true, y_pred)
    nmi = normalized_mutual_info_score(y_true, y_pred)
    return ari, nmi


for threshold in THRESHOLDS:
    for min_samples in MIN_SAMPLES_VALUES:
        labels = dbscan(sim, threshold=threshold, min_samples=min_samples)
        ari, nmi = external_validation(ids, labels, true_labels)
        print(f"threshold={threshold}, min_samples={min_samples}: ARI={ari:.3f}, NMI={nmi:.3f}")


def internal_validation(sim, embeddings, labels):
    """Silhouette + Davies-Bouldin across all articles in all clusters. 
    silhouette_score can take a precomputed distance matrix (1 - cosine
    similarity), doesn't need embeddings directly. davies_bouldin_score
    computes cluster centroids internally, has to have real feature vectors.
    Hence why it takes embeddings, not the similarity matrix.
    """
    labels = np.array(labels)
    mask = labels != -1

    if len(set(labels[mask])) < 2:
        return None

    distance = np.clip(1 - sim, 0, None)
    silhouette = silhouette_score(distance[np.ix_(mask, mask)], labels[mask], metric="precomputed")
    db = davies_bouldin_score(embeddings[mask], labels[mask])
    return silhouette, db


for threshold in THRESHOLDS:
    for min_samples in MIN_SAMPLES_VALUES:
        labels = dbscan(sim, threshold=threshold, min_samples=min_samples)
        result = internal_validation(sim, embeddings, labels)
        if result is None:
            print(f"threshold={threshold}, min_samples={min_samples}: too few clusters for internal validation")
            continue
        silhouette, db = result
        print(f"threshold={threshold}, min_samples={min_samples}: silhouette={silhouette:.3f}, DB={db:.3f}")
