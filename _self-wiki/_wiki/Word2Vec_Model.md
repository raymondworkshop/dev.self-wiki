---
title: Word2Vec Model
last_updated: '2026-05-21T00:45:33.494702'
description: A technical overview of the Word2Vec model, its underlying mechanics
  (Skip-grams, CBOW), and its application in distributed word representation.
level: 1
tags:
- type/principle
- technical/ML
- topic/NLP
alias: Word2Vec Model
---

> This entry introduces Word2Vec as a neural network model capable of producing dense vector representations for words in a corpus. These vectors encode valuable syntactic and semantic information derived from the training data. The mechanics discussed include Skip-grams (SG) and Continuous Bag of Words (CBOW).



### Distillation (2026-05-21) - source: [[../raw/diary/tech/2017-07-20-word2vec.md]]
## Word2Vec Model

Word2Vec is a class of neural network models trained on an unlabeled training corpus. Its function is to generate a vector for each word that encodes its valuable syntactic and semantic information.

### Skip-grams (SG)
Predict context words given a target word (position independent).

### Continuous Bag of Words (CBOW)
Predict the target word from a bag-of-words context.

### Underlying Mechanics
* Stochastic Gradient Descent

### References
* Linguistic Regularities in Continuous Space Word Representations
* [The amazing power of word vectors](https://blog.acolyer.org/2016/04/21/the-amazing-power-of-word-vectors/)
* [Word2vec tutorial](http://mccormickml.com/assets/word2vec/Alex_Minnaar_Word2Vec_Tutorial_Part_I_The_Skip-Gram_Model.pdf)


## Evolution


## Backlinks


## Sources
- [[../raw/diary/tech/2017-07-20-word2vec.md]]
