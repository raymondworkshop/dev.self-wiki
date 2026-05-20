---
last_updated: 2024-05-29T12:00:00Z
title: Natural Language Processing and Linguistics Overview
description: A technical overview of the components of human language, including phonetics, morphology, syntax, semantics, and modern computational approaches like word embeddings.
tags: [type/principle, knowledge_base, technical]
---

> This document provides a foundational overview of human language as a symbolic signaling system and details the various linguistic levels involved in its structure and meaning. It contrasts traditional linguistic analysis with modern computational approaches used in Natural Language Processing (NLP).

## Evolution
- Initial entry established the core components of language (phonetics, morphology, syntax, semantics, pragmatics) and introduced computational models like Word Vectors and Language Modeling.

## Content

### Human Language
A human language is fundamentally a symbolic signaling system. Most words function as symbols mapping to an extra-linguistic entity (an idea or thing). The encoding of these symbols (voice, gesture, writing) involves continuous signals to the brain, making its exploration a problem at the intersection of psychology, cognitive science, and computation (e.g., the Turing Test).

### About Languages (Linguistic Levels)
The structure of language is analyzed across several interdependent levels:

*   **Phonetics:** The physical properties of speech sounds.
*   **Phonology:** The study of the sound patterns of a specific language.
    *   **Sound Production/Perception:** Includes concepts like word stress (vowels in unstressed syllables pronounced as schwa /ə/) and the ability to modify pitch, volume, or duration to create contrast.
    *   **Intonation:** Can reflect syntactic or semantic differences.
*   **Morphology:** The rules governing word formation.
    *   **Morphemes:** The smallest units of meaning.
*   **Syntax:** The rules governing how words combine into phrases and sentences.
*   **Semantics:** The linguistic meaning conveyed.
    *   **Lexical Semantics:** The meaning inherent in individual words.
*   **Pragmatics:** How context influences the interpretation of meaning.

### Computational Approaches (NLP)

Modern NLP seeks to model these phenomena computationally:

*   **Word Vectors/Embeddings:** These produce dense vector representations of words based on context.
    *   **Distributed Representations:** Modern models rely on the hypothesis that distributional similarity holds—words appearing in similar contexts tend to have similar meanings.
    *   **Word2Vec Model:** Demonstrates how a word's meaning can be inferred from its neighbors, encoding valuable semantic information.
*   **Language Modeling:** This involves probabilistic models predicting sequences of words.
    *   **Models:** Include N-gram models, Finite Automata, RNNs, and LSTM Networks.
*   **Parsing:** The process of determining the grammatical structure (tree structure) of a sentence.

## Backlinks
<!-- BEGIN BACKLINKS -->
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/diary/2017-05-19-nlp.md]]