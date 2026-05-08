---
layout: post
title: "Similarity Search Algorithms"
date: 2015-09-04
comments: true
categories: [home, algorithms]
abstract: "Similarity search refers to finding objects that have similar characteristics to the query object."
---

> Similarity search refers to finding objects that have similar characteristics to the query object.

#### Similarity Search [^1]

-   Similarity Search in high-dimensional spaces becomes increasingly important in databases, data mining, and search engines,particularly for content-based search of feature-rich data such as audio recordings, digital photos, digital videos and other sensor data. Since feature-rich data objects are typically represented as high-dimensional feature vectors.

-   The problem of similarity search refers to finding objects that have similar characteristics to the query object. Similarity search is usually implemented as K-Nearest Neighbor (KNN) or Approximate Nearest Neighbors (ANN) search in high-dim feature-vector space.

    -   KNN: find the K objects that are closest to q according to a distance function
    -   ANN: find K objects whose distances are within a small factor (1 + x) of the true K-nearest neighbors's distances

-   An ideal indexing scheme for similarity search:
    -   Accurate: very close to those of the brute-force, linear-scan approach
    -   Time efficient: O(logN)
    -   Space efficient: the index data structure may even fit into main memory
    -   High-dimensional: the indexing scheme should work well for datasets with very high intrinsic
        dimensionalities

#### The related approaches

-   tree-based indexing methods for K-Nearest Neighbor(KNN)

    -   K-D tree: not time efficient for data with high-dim

    -   TODO

-   the indexing method: LSH [^1]

    -   use hash functions to **map similar objects into the same hash buckets with high probability** .

        using LSH functions to select candidate objects for a given query q,
        and ranking the candidate objects according to their distances to q.

    -   Drawback: to achieve high search accuracy, the LSH method needs to use multiple hash tables to produce a good candidate set.

        -   Experimental studies show that the basic LSH needs hundreds hash tables to achieve good search accuracy for high-dimensional datasets.

        -   The size of each hash table is proportional to the number of data objects, since each table has **as many
            entries as the number of data objects** in the dataset.
            When the space requirement for the hash tables exceeds the main memory size, looking up a hash bucket may require a disk I/O, causing substantial delay to the query process.

    -   The approach does not satisfy the space-efficiency requirement.

-   Multi-probe LSH [^1]

    -   The main idea is to build on the basic LSH indexing method, but to use **a carefully derived probing
        sequence to look up multiple buckets** that have a high probability of containing the nearest neighbors of a query object.

    -   Given the property of LSH, if an object is close to a query object q but not hashed to the same bucket as q, it is likely to be in **a buckets that is "close by"** (i.e. the hash values of the two buckets only differ slightly).

    -   By probing multiple buckets in each hash table, the method requires far fewer hash tables than previous LSH methods

[^1]: "Multi-probe LSH: Efficient indexing for high-dimensional similarity search" by Q.Lv, W.Josephson, Z. Wang, M. Charikar, and K. Li, VLDB
