---
last_updated: 2024-05-20T12:00:00Z
title: Hash Table Fundamentals
description: A technical deep dive into the theory and implementation of hash functions and hash tables, covering collision resolution and performance trade-offs.
tags: [type/principle, work, cognitive_modeling]
---

> This document introduces the theoretical underpinnings of hash functions, detailing how they map keys to array indices for efficient data retrieval. It contrasts the time complexities of hashing versus traditional search structures like binary search trees.

## Evolution
- Initial concepts regarding hashing were purely theoretical, focusing on the mapping process. The current structure integrates practical collision resolution techniques (chaining, probing) and performance considerations (capacity selection).

## Content
### Introduction to Hashing
Hashing is a technique used to map an input key of arbitrary size into a fixed-size array index.
- **Time Complexity Trade-off**: While a sorted structure allows $O(\log N)$ search time with $O(N)$ space, hashing aims for $O(1)$ expected time complexity for dictionary queries, albeit requiring $O(N)$ space.
- **Two-Step Process**: Efficient key-value pair referencing involves:
    1. Computing a **hash function** to transform the search key into an array index.
    2. Applying a **collision-resolution process** to handle cases where different keys map to the same index.

### Hash Functions
A hash function $h$ maps a universe of keys $U$ into a target range $T = \{0, 1, \dots, m-1\}$.
- **Uniform Hashing Assumption**: Assumes any key in $U$ is equally likely to map to any of the $m$ slots, independently of other keys. For distinct keys $k_1, k_2$, the probability of collision is $\text{Pr}(h(k_1)=h(k_2)) \leq 1/m$.
- **Qualities of a Good Hash Function**:
    - **Deterministic**: Identical keys must always produce the same hash value.
    - **Efficient to Compute**: The calculation must be fast.
    - **Uniform Distribution**: Keys must be distributed equally across the $m$ indices. Poor distribution increases collisions, degrading performance.

#### Hashing Techniques
- **Hashing by Division**: $h(k) = k \pmod m$. This performs well if $m$ is a prime number unrelated to key patterns.
- **Hashing by Multiplication**: (Mentioned but not detailed in the source).
- **Universal Hashing**: (TODO in source).

### Collision Resolution Strategies
When two or more keys map to the same slot (a collision), resolution strategies are needed:
- **Separate Chaining**: Each slot holds a linked list containing all key-value pairs that hash to that index. The list length must be kept short for efficient searching.
- **Open Addressing (Linear Probing)**: All key-value pairs are stored directly in the hash table array. If the initial slot is occupied, subsequent slots are probed sequentially until an empty spot is found.

### Performance Considerations
- **Capacity ($m$) Selection**: $m$ must be large enough to minimize chain length but small enough to avoid excessive memory waste.
- **Advantages of Hash Tables**:
    - Keys do not need to be ordered types.
    - Constant-time performance can be achieved in practice.
- **Disadvantages**:
    - Retrieval in sorted order is difficult.
    - Finding a fast, good hash function can be challenging.
    - Resizing the table is an expensive operation, making them unsuitable for some real-time systems.

## Evolution
- The initial understanding was a high-level comparison between hashing and array/tree structures. The current version provides a rigorous technical breakdown, including specific collision resolution methods and performance constraints, moving from conceptual comparison to implementation detail.

## Backlinks
<!-- BEGIN BACKLINKS -->
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/diary/2015-07-11-hash.md]]