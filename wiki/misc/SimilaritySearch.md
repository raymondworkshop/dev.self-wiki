---
last_updated: 2024-07-08T00:00:00Z
title: Similarity Search Algorithms
description: This document details algorithms for finding objects similar to a query object, focusing on the trade-offs between accuracy, time efficiency, and space efficiency in high-dimensional data.
tags:
  - algorithms
  - information-retrieval
  - machine-learning
#type/principle
---
# Similarity Search

Similarity Search involves locating objects that share characteristics with a query object, a critical task in modern databases, data mining, and search engines dealing with high-dimensional feature vectors (e.g., audio, images).

## Core Problems

The problem is typically framed as finding the $K$ objects closest to the query object ($q$) according to a defined distance function.

*   **K-Nearest Neighbor (KNN)**: Find the $K$ objects closest to $q$.
*   **Approximate Nearest Neighbors (ANN)**: Find $K$ objects whose distances are within a small factor $(1+x)$ of the true $K$-nearest neighbors' distances.

## Ideal Indexing Scheme Requirements
An ideal indexing scheme must balance three properties:
1.  **Accuracy**: Must closely approximate the brute-force, linear-scan approach.
2.  **Time Efficiency**: Query time complexity should ideally be $O(\log N)$.
3.  **Space Efficiency**: The index structure should ideally fit within main memory.

## Approaches

### Tree-based Indexing
*   **K-D Tree**: A viable method for KNN search, though its time efficiency degrades significantly with high dimensionality.

### Locality-Sensitive Hashing (LSH)
LSH uses hash functions to map similar objects into the same hash buckets with high probability.
*   **Basic LSH**: Requires many hash tables (hundreds for high accuracy in high dimensions) to achieve good search accuracy, leading to poor space efficiency if each table scales with the dataset size.
*   **Multi-probe LSH**: An advancement that uses a carefully derived probing sequence to check multiple buckets per hash table. This significantly reduces the required number of hash tables compared to basic LSH.

---
## Evolution
This note has evolved from a general definition of the problem into a comparative analysis of indexing strategies (KNN vs. ANN) and a deep dive into the trade-offs inherent in scaling LSH implementations.

## Sources
- raw/diary/2015-09-04-similaritysearch.md
---
## Backlinks
<!-- BEGIN BACKLINKS -->
- **Mentioned in**: [[Clustering Algorithms]], [[HighDimensionalData]]
<!-- END BACKLINKS -->