---
last_updated: 2024-05-29T12:00:00Z
title: Similarity Search Algorithms
description: A technical overview of similarity search techniques, including KNN and ANN, and indexing methods like LSH.
tags: [type/principle, work, cognitive_modeling]
---

> Similarity search involves efficiently finding objects in a dataset that share similar characteristics with a given query object, particularly in high-dimensional feature spaces. This is crucial for modern applications like content-based search in large databases.

## Content

### Similarity Search [^1]

Similarity Search in high-dimensional spaces becomes increasingly important in databases, data mining, and search engines, particularly for content-based search of feature-rich data such as audio recordings, digital photos, digital videos and other sensor data. Since feature-rich data objects are typically represented as high-dimensional feature vectors.

The problem of similarity search refers to finding objects that have similar characteristics to the query object. Similarity search is usually implemented as K-Nearest Neighbor (KNN) or Approximate Nearest Neighbors (ANN) search in high-dim feature-vector space.

-   **KNN**: find the K objects that are closest to q according to a distance function
-   **ANN**: find K objects whose distances are within a small factor (1 + x) of the true K-nearest neighbors's distances

An ideal indexing scheme for similarity search:
-   **Accurate**: very close to those of the brute-force, linear-scan approach
-   **Time efficient**: O(logN)
-   **Space efficient**: the index data structure may even fit into main memory
-   **High-dimensional**: the indexing scheme should work well for datasets with very high intrinsic dimensionality

### The related approaches

#### Tree-based indexing methods for K-Nearest Neighbor (KNN)
-   **K-D tree**: not time efficient for data with high-dim
-   **TODO**

#### The indexing method: LSH [^1]
-   Use hash functions to **map similar objects into the same hash buckets with high probability**.
    -   Using LSH functions to select candidate objects for a given query q, and ranking the candidate objects according to their distances to q.
-   **Drawback**: to achieve high search accuracy, the LSH method needs to use multiple hash tables to produce a good candidate set.
    -   Experimental studies show that the basic LSH needs hundreds hash tables to achieve good search accuracy for high-dimensional datasets.
    -   The size of each hash table is proportional to the number of data objects, since each table has **as many entries as the number of data objects** in the dataset. When the space requirement for the hash tables exceeds the main memory size, looking up a hash bucket may require a disk I/O, causing substantial delay to the query process.
    -   The approach does not satisfy the space-efficiency requirement.

#### Multi-probe LSH [^1]
-   The main idea is to build on the basic LSH indexing method, but to use **a carefully derived probing sequence to look up multiple buckets** that have a high probability of containing the nearest neighbors of a query object.
-   Given the property of LSH, if an object is close to a query object q but not hashed to the same bucket as q, it is likely to be in **a buckets that is "close by"** (i.e. the hash values of the two buckets only differ slightly).
-   By probing multiple buckets in each hash table, the method requires far fewer hash tables than previous LSH methods.

## Evolution
- This page is a direct transcription and initial structuring of technical notes regarding Similarity Search algorithms. Future updates will involve cross-referencing these concepts with broader cognitive models of efficiency and trade-offs.

## Backlinks
<!-- BEGIN BACKLINKS -->
- **Mentioned in**: [[Cognitive_Modeling_of_Efficiency]] (Hypothetical)
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/diary/2015-09-04-similaritysearch.md]]