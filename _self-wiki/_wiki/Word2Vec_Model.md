---
last_updated: 2024-05-29T12:00:00Z
title: Word2Vec Model
description: A technical overview of the Word2Vec neural network models used for distributed word representations.
tags: [type/principle, work, cognitive]
---

> Word2Vec is a class of neural network models trained on an unlabeled corpus to generate dense vector representations for each word, encoding its syntactic and semantic information. These models, including Skip-grams (SG) and Continuous Bag of Words (CBOW), are foundational in modern NLP.

## Evolution
- Initial conceptualization of word vectors as a method to capture word meaning in a distributed, numerical format.

## Content
### Distributed Representations of Words
Word2Vec models produce a vector for each word in the corpus, encoding its valuable syntactic and semantic information after training on an unlabelled corpus.

### Model Types
1. **Skip-grams (SG)**: Predict context words given a target word (position independent).
2. **Continuous Bag of Words (CBOW)**: Predicts the target word from its surrounding context words.

### Training Mechanism
The models are trained using techniques such as Stochastic Gradient Descent.

## Backlinks
<!-- BEGIN BACKLINKS -->
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/diary/tech/2017-07-20-word2vec.md]]