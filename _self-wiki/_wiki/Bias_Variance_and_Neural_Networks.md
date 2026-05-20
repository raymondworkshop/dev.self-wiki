---
last_updated: 2024-05-29T12:00:00Z
title: Bias, Variance, and Neural Networks
description: A technical breakdown of model fitting concepts (Bias, Variance) applied to neural network training, including specific algorithms like Gradient Descent and Dropout.
tags: [type/principle, work, cognitive_model]
---

> This document synthesizes technical concepts regarding model fitting in machine learning, specifically addressing the trade-off between bias and variance in the context of neural networks. It outlines the roles of various algorithms like Gradient Descent and Dropout in achieving robust model performance.

## Evolution
- Initial concepts regarding model fitting were introduced in the raw data. This page structures these concepts into a formal technical comparison.

## Content
### Basics: Model Fitting Concepts

*   **Bias (偏差)**: Represents the difference between the expected value of the model and the true value. A high bias suggests the model is too simple or lacks the necessary complexity to capture the underlying pattern (underfitting).
*   **Variance (方差)**: Describes the degree of variability in the model's predictions. High variance indicates the model is overly sensitive to the training data noise, leading to poor performance on unseen data (overfitting).

**Neural Network Dynamics:**
Neural networks possess high fitting capacity. Therefore, they often exhibit low training error (low bias) but, if not properly regularized, can suffer from high variance, resulting in high test error.

**Mitigation Strategies:**
*   **Regularization**: Techniques aimed at reducing test error, collectively known as regularization methods.
*   **Dropout**: A powerful technique used in CNNs to prevent overfitting and improve model generalization.

**Training Algorithms:**
*   **Gradient Descent**: Uses the loss function to find local minima by calculating the gradient across all parameters.
*   **Backpropagation**: An algorithm utilizing the chain rule of calculus to compute gradients with respect to the parameters.

**Model Types:**
*   **Word2Vec**: A "predictive" model, predicting context words based on a target word, or vice versa.
*   **GloVe**: A "count-based" model.

### Module: Supervised Learning
The fundamental framework is defined as $Y = f(X)$.

## Backlinks
<!-- BEGIN BACKLINKS -->
- **Evolved from**: [[self-wiki/raw/diary/self/2019-04-07-interview.md]]
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/diary/self/2019-04-07-interview.md]]