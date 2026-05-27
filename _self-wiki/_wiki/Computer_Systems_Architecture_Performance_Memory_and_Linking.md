---
title: 'Computer Systems Architecture: Performance, Memory, and Linking'
last_updated: '2026-05-20T23:09:29.498463'
description: A detailed technical summary of computer science concepts including compiler
  optimization, memory hierarchy management, linking processes, and exceptional control
  flow.
level: 1
tags:
- topic/technical_fundamentals
- type/principle
- topic/algorithms
- memory_management
- topic/machine_learning
- technical_overview
- computer_science
- type/synthesis
- topic/data_structures
alias: On Interview
---

> This document provides a technical overview of computer systems, covering performance optimization trade-offs, the memory hierarchy (exploiting locality), and the mechanics of linking (static vs. dynamic). It details how these components interact to manage execution flow from the CPU cycle to physical storage access.

### Distillation (2026-05-20) - source: [[../raw/diary/2017-05-16-an-overview-of-computer-system.md]]

### Distillation (2026-05-20) - source: [[../raw/diary/2014-05-25-search-algorithms-binary-search-trees.md]]

### Distillation (2026-05-20) - source: [[../raw/diary/self/2019-04-07-interview.md]]
## Socratic Summary
This raw data compares Bias and Variance in machine learning models, relating them to the concepts of fitting ability and stability. It contrasts the roles of gradient descent, backpropagation, and dropout in model training and regularization.

### Technical Concepts Distilled

**Bias (偏差):**
*   **Definition:** The difference between expected value and true value (期望值和真实值 之间的差).
*   **Indication:** Describes the model's fitting ability (拟合能力). High bias suggests insufficient model complexity.

**Variance (方差):**
*   **Definition:** The degree of dispersion in model predictions (模型预测的离散程度).
*   **Indication:** Describes model stability. High variance suggests overfitting or excessive complexity.

**Tradeoff:**
*   Neural networks often have low training error (low bias) due to high fitting ability, but this strong fitting can lead to high variance and large test error.

**Optimization & Training Methods:**
*   **Gradient Descent:** Uses the loss function to find local minima by calculating gradients across all parameters.
*   **Backpropagation:** A gradient-based method using the chain rule to calculate parameter derivatives.
*   **Non-linear Activation Functions:** Introduce non-linearity to enhance the network's representational capacity.
*   **Dropout:** A technique used in CNNs to prevent overfitting and improve performance.

**Model Types:**
*   **Supervised Learning:** $Y = f(X)$.
*   **Word2Vec:** A "predictive" model, predicting context from intermediate words, or vice versa.
*   **GloVe:** A "count-based" model.


## Evolution


## Backlinks


## Sources
- [[../raw/diary/2014-05-25-search-algorithms-binary-search-trees.md]]
- [[../raw/diary/2017-05-16-an-overview-of-computer-system.md]]
- [[../raw/diary/self/2019-04-07-interview.md]]
