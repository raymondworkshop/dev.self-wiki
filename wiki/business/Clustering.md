---
last_updated: 2024-07-08T00:00:00Z
title: Clustering Algorithms
description: This note provides a technical comparison of unsupervised machine learning techniques for grouping data points, detailing k-means, k-center, and hierarchical methods.
tags:
  - machine-learning
  - algorithms
  - data-science
#type/principle
---
# Clustering Algorithms

Clustering is the process of dividing a set of objects into meaningful groups based on the similarity of their attributes. The goal is to ensure objects within the same cluster are highly similar, while objects in different clusters are dissimilar.

## Centroid-based Partitioning

### k-means
k-means is an iterative algorithm used to partition data into $k$ clusters.
1.  **Initialization**: Select $k$ initial centroids (e.g., $k$ random points).
2.  **Assignment**: Assign every data point to the nearest centroid.
3.  **Update**: Recalculate the centroid as the average of all points assigned to that cluster.
4.  **Termination**: Repeat steps 2 and 3 until the centroid set no longer updates significantly.
*   **Guarantee**: The algorithm is guaranteed to terminate after a finite number of rounds. Each round strictly lowers the cost (distance) of the centroid set.
*   **Refinement (k-means++)**: To improve the initial centroid selection, use $k$-seeding, where each point is chosen as a centroid with a probability proportional to $(D(p)^2)$. This addresses the arbitrary nature of initial centroid selection.

### k-center
k-center aims to find a set of $k$ centers that minimizes the maximum distance from any point to its nearest center.
*   **Goal**: Find the $k$-center set with the smallest radius ($r^*$).
*   **Complexity**: Finding the optimal $k$-circle cover is NP-hard, but a 2-approximate solution can be achieved.

## Hierarchical Methods

Hierarchical clustering builds a hierarchy of clusters, allowing users to explore different levels of granularity.
*   **Agglomerative Method**: Starts with each object as its own cluster and iteratively merges the two most similar clusters until a single cluster remains.
*   **Dendrogram**: The merging history can be visualized as a tree structure.
*   **Efficiency**: Using a Binary Search Tree (BST) to store inter-cluster distances allows for efficient merging, achieving $O(n^2 \cdot \log n)$ complexity.

## Density-based Methods
(TODO)

---
## Evolution
This note has evolved from initial conceptualization into a detailed technical comparison of algorithms, including specific complexity analysis and advanced seeding techniques like $k$-means++.

## Sources
- raw/diary/2015-07-29-clustering.md
---
## Backlinks
<!-- BEGIN BACKLINKS -->
- **Mentioned in**: [[SimilaritySearch]], [[DataMining]]
<!-- END BACKLINKS -->