---
title: 'Clustering Algorithms: Centroid-based, Hierarchical, and Density-based Approaches'
last_updated: '2026-05-20T20:37:51.226992'
description: A technical review of various algorithms used to partition data into
  meaningful groups, focusing on the mechanics, termination conditions, and computational
  complexity of each method.
level: 1
tags:
- algorithm
- technical_review
- machinelearning
- type/synthesis
alias: 'Clustering Algorithms: Centroid-based, Hierarchical, and Density-based Approaches'
---

> This document provides a technical summary of unsupervised clustering methods, detailing Centroid-based (k-means, k-center), Hierarchical (agglomerative), and Density-based approaches. It contrasts the termination guarantees of k-means with the approximation bounds of k-center, and outlines the mechanics of agglomerative clustering using dendrograms.



### Distillation (2026-05-20) - source: [[../raw/diary/2015-07-29-clustering.md]]
## Clustering Algorithms

#### Clustering
Divide a set of objects into meaningful groups.

#### Centroid-based partitioning
Objects in the same cluster should be similar; objects in different clusters should be dissimilar.

- **k-center**: Find the k center set with the smallest radius $r^*$.
    - NP-hard.
    - Optimal k-circle cover provides a 2-approximate k-circle cover, achievable by selecting a random point first and then maximizing the distance to subsequent points.

- **k-mean**
    - Initialization: Start with $k$ random points as initial centroids.
    - Iteration: Assign all points to the closest centroid; update the centroid as the average of all assigned points.
    - Termination: The algorithm always terminates because the cost (distance) of the centroid set strictly decreases with each round.
    - Accuracy Enhancement: k-means++ uses probabilistic seeding proportional to $D(p)^2$ to improve the approximation ratio, addressing the arbitrariness of initial centroid selection.
    - Limitation: Struggles with clusters of differing sizes, densities, or non-globular shapes.

#### Hierarchical Methods
Used when users need to explore various clustering results efficiently.

- **Agglomerative Method**: Merge the two most similar clusters until only one remains.

- **Implementation**: A dendrogram represents the merging history.
    - The process uses a Binary Search Tree (BST) to store distances between current clusters.
    - At each step, the smallest cluster-pair distance is removed from the BST, and the pair is merged into a new cluster.
    - Complexity: $O(n^2 \cdot \log n)$ (depending on implementation details).

#### Density-based
- TODO

#### References
- [Data Mining and Knowledge Discovery](http://www.cse.cuhk.edu.hk/~taoyf/course/cmsc5724/spr15/cmsc5724.html)
- [FLANN lib](http://www.cs.ubc.ca/research/flann/)


## Evolution


## Backlinks


## Sources
- [[../raw/diary/2015-07-29-clustering.md]]
