---
last_updated: 2024-05-29T12:00:00Z
title: Locality-Sensitive Hashing and Fingerprints
description: A technical synthesis of Locality-Sensitive Hashing (LSH) algorithms applied to the minutiae representation of fingerprints.
tags: [type/synthesis, work, principle]
---

> This document synthesizes concepts from fingerprint minutiae analysis and Locality-Sensitive Hashing (LSH) algorithms. It details how LSH projects high-dimensional data into a low-dimensional space to efficiently find similar items, mirroring the structural analysis used in fingerprint matching.

## Evolution
- Initial concepts regarding fingerprint minutiae were combined with the mathematical framework of LSH to create a unified technical overview.

## Content

### Fingerprint Minutiae Analysis
Fingerprint ridges possess specific features called minutiae, which are crucial for unique identification. These features include ridge endings, bifurcations, and short ridges or dots.
- **Minutia Definition**: A minutia is a point where an unusual event occurs in the ridge pattern, such as two ridges merging or a ridge terminating.
- **MCC Representation**: The Minutia Cylinder-code (MCC) associates a local structure (represented by a "cylinder") to each minutia, normalizing the fingerprint image for size and orientation to allow for comparison.

### Locality-Sensitive Hashing (LSH)
LSH is an algorithmic technique used to address the high-dimensional nearest neighbor search problem efficiently.
- **Core Concept**: LSH projects data into a lower-dimensional space such that similar items are mapped to the same hash buckets with high probability. Candidate pairs for comparison are those that collide in one or more hash buckets.
- **Efficiency**: LSH drastically reduces the number of distance calculations required by only considering vectors that collide with the query vector under the hash functions.
- **Application to Euclidean Distance**: For Euclidean distance, LSH can be initialized by projecting points onto random lines. A pair of points is considered "yes" if they fall into the same fixed-length interval along a projected line.

### Synthesis: LSH and Fingerprints
The MCC representation provides the local structure data, while LSH provides the scalable method to compare these high-dimensional structures. The goal is to use LSH to quickly identify candidate matches among a large database of fingerprints by exploiting the local similarity encoded in the minutiae structures.

## Backlinks
<!-- BEGIN BACKLINKS -->
- **Mentioned in**: [[Self_Assessment_and_Life_Goals.md]] (Potential conceptual link regarding efficiency/scale)
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/diary/2015-03-20-mcc_lsh.md]]