---
last_updated: 2024-05-29T12:00:00Z
title: Clustering Algorithms Synthesis
description: A technical summary of various clustering algorithms including k-center, k-means, and hierarchical methods.
tags: [type/synthesis, work, machinelearning]
---

> This document synthesizes technical approaches to clustering, dividing objects into meaningful groups based on similarity. It covers centroid-based methods like k-means and k-center, as well as hierarchical approaches.

## Evolution
- Initial concepts regarding clustering algorithms were documented in the raw source file. This page serves to structure and synthesize these concepts into a navigable knowledge base.

## Content

### Clustering - Divide a set of objects into meaningful groups

#### Centroid-based partitioning

**k-center:**
- Finds the k center set with the **smallest radius r***.
- NP-hard problem.
- An optimal k-circle cover provides a 2-approximate k circle cover, achievable by:
    1. Choosing a random point first.
    2. Then choosing the point with the maximum distance to the current set.

**k-mean:**
- **Process:**
    1. Initialize with **k random points** as initial centroids.
    2. Form k clusters by assigning all points to the closest centroid.
    3. Update the centroid to be the **average of all coordinates of the points in this cluster**.
    4. Terminate when the centroid set does not update.
- **Guarantees:**
    - The algorithm always terminates.
    - After each round, the cost (distance) of the centroid set is strictly lower than the previous set.
- **Refinements:**
    - **k-seeding (k-means++):** Each point is chosen as a centroid with a probability proportional to $(D(p))^2$. This improves the approximation ratio by moving beyond arbitrarily chosen initial centroids.
- **Limitations:**
    - Struggles with differing sizes, differing densities, and non-globular shapes.

#### Hierarchical Methods

**Why use them:**
- Allows different users to explore the hierarchy to obtain **various** clustering results efficiently when the clustering requirement is complex.

**How (Agglomerative Method):**
- Merge the two most similar clusters until only one cluster remains.

**Implementation Details:**
- A dendrogram represents the merging history as a tree.
- To obtain k clusters from a dendrogram, the merging history must be interpreted.
- **Algorithmic Approach:**
    1. Use a **binary search tree (BST)** to store the distances of all pairs of current clusters.
    2. In each step, remove the smallest cluster-pair distance from T and merge them into a new cluster.
    - Time complexity: $O(n^2 \cdot \log n)$.
    - The distance function is crucial (TODO).

#### Density-based
- TODO

## Backlinks
<!-- BEGIN BACKLINKS -->
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/diary/2015-07-29-clustering.md]]