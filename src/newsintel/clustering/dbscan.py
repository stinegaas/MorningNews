from __future__ import annotations
import sqlite3
import numpy as np
from newsintel.features.embeddings import load_embedding


def load_similarity_matrix(conn: sqlite3.Connection) -> tuple[list[int], np.ndarray]:
    """Returns (article_ids, similarity_matrix). article_ids[i] is the article
    that row/column i of similarity_matrix belongs to.

    Embeddings are L2-normalized (see features/embeddings.py) -> cosine similarity between two vectors 
    is just the dot product. The whole pairwise matrix is one matrix multiplication, no per-pair loop needed.
    """

    rows = conn.execute("SELECT article_id, embedding FROM article_embeddings").fetchall()

    article_ids = [article_id for article_id, _ in rows]
    embeddings = np.vstack([load_embedding(blob) for _, blob in rows])

    similarity_matrix = embeddings @ embeddings.T
    return article_ids, similarity_matrix


def find_neighbors(similarity_matrix, i, threshold) -> list[int]:
    """
    Find the neighbors of a point in the similarity matrix based on a threshold.

    Args:
        similarity_matrix (np.ndarray): 2D array representing the similarity between points.
        i (int): The index of the point for which to find neighbors.
        threshold (float): The similarity threshold to consider a point as a neighbor.

    Returns:
        list[int]: A list of indices of neighboring points.
    """
    neighbors = []
    for j in range(similarity_matrix.shape[0]):
        if i != j and similarity_matrix[i, j] >= threshold:
            neighbors.append(j)
    return neighbors



def dbscan(similarity_matrix, threshold, min_samples) -> list[int]:
    """
    Perform DBSCAN clustering on a similarity matrix.

    Args:
        similarity_matrix (np.ndarray): A 2D array representing the similarity between points.
        threshold (float): The similarity threshold to consider a point as a neighbor.
        min_samples (int): The minimum number of neighbors required to form a dense region.

    Returns:
        list[int]: A list of cluster labels for each point. Noise points are labeled as -1.
    """
    n_points = similarity_matrix.shape[0]
    labels = [-1] * n_points  # Initializes all points as noise
    cluster_id = 0

    for i in range(n_points):
        if labels[i] != -1:  # if already processed, skip
            continue

        neighbors = find_neighbors(similarity_matrix, i, threshold)

        if len(neighbors) < min_samples:
            labels[i] = -1  # Mark as noise
        else:
            # Start a new cluster
            labels[i] = cluster_id

            # Check if the current point has neighbors that can be added to the cluster
            seeds = neighbors.copy() 

            while seeds:
                neighbor = seeds.pop() # retreives last neighbor in list, removes it from the list

                if labels[neighbor] != -1:  # Already assigned to a cluster
                    continue
                labels[neighbor] = cluster_id
                neighbors_neighbors = find_neighbors(similarity_matrix, neighbor, threshold)
                if len(neighbors_neighbors) >= min_samples:
                    seeds.extend(neighbors_neighbors)  # Add neighbors of the neighbor to the seeds list

            cluster_id += 1

    return labels