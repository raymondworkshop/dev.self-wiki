---
last_updated: 2026-05-07
sources:
  - raw/origin-apple-notes/git.md
  - raw/origin-apple-notes/data.md
  - raw/origin-apple-notes/engineering.md
  - raw/origin-apple-notes/tech.md
  - raw/origin-apple-notes/programming.md
  - raw/origin-apple-notes/Why open source.md
  - raw/diary/2023-10-06-programming-languages.md
  - raw/diary/2024-11-29-notes-on-llm.md
  - raw/diary/research/2019-07-08-about-ai.md
  - raw/diary/research/2018-11-18-research-notes.md
  - raw/diary/research/2020-08-29-science.md
  - raw/diary/tech/2014-05-29-building-abstractions-with-procedures.md
  - raw/diary/tech/2017-07-20-word2vec.md
  - raw/diary/tech/2017-07-21-logistic-regression.md
  - raw/diary/tech/2018-03-04-REST-architecture.md
  - raw/diary/tech/2019-04-30-deep-learning.md
  - raw/diary/tech/2019-07-17-machine-learning-systems.md
  - raw/diary/tech/2019-12-11-concurrency.md
tags:
  - algorithms
  - computer-science
  - software-engineering
  - tech-stack
  - open-source
  - ai
  - research
---

Technology encompasses the study of algorithms, system architecture, and software engineering principles. It serves as a computational language for understanding nature and building efficient, evolvable tools for problem-solving.

### Software Engineering Principles

#### Evolvability vs. Point-in-Time Correctness
The most important attribute of code is not whether it runs correctly at a specific moment, but whether it can **evolve correctly at low cost over time**. 
- **Complexity**: A 100,000-line complex function is a failure of engineering because it is impossible to evolve.
- **Maintainability**: Code should be written for the future self and other maintainers.
- **Abstractions**: Building abstractions via procedures is the fundamental mechanism for controlling complexity in computer programs; it allows for the modular decomposition of problems into manageable, reusable components.

#### Skill Mastery
- **Value-Driven Passion**: Don't just "find your passion." Master a skill, interest, or knowledge that others find valuable. Mastery leads to rewards and the freedom to pursue work you enjoy.
- **Practical Tools**: 
    - **Debugging**: Use `pdb` for Python.
    - **Testing**: Implement `pytest` for robust verification.
    - **Formatting**: Use `black` for consistent code style.

### Tech Stack and Infrastructure
- **Backend**: Python / Django for robust service architecture.
- **Web Services**: Node.js and TypeScript for scalable web layers, and RESTful architecture for structured, stateless communication between distributed components.
- **Frontend**: React for modern, component-based user interfaces.
- **Infrastructure**: AWS for cloud-native deployment and management.
- **Version Control**: Git (and platforms like GitHub) for collaborative development.

### Algorithms and Data Structures

#### Core Foundations
- **Searching and Sorting**: Binary Search ($O(\log N)$), BST, and Priority Queues (Binary Heaps).
- **Hashing**: Hash Tables for $O(1)$ lookups and Locality-Sensitive Hashing (LSH) for high-dimensional similarity.
- **Machine Learning**: 
    - **Logistic Regression**: A linear model for binary classification problems.
    - **Word2Vec**: An architecture to generate word embeddings by learning vector representations in a continuous space based on context.
    - **Deep Learning**: Neural network structures capable of learning complex representations from data.
    - **Clustering**: K-means++, Face Recognition (PCA).
- **Concurrency**: Managing state in parallel processes requires understanding locking, atomic operations, and avoiding deadlocks to ensure system integrity.

### Computer Systems, Research, and AI

#### Research Methodology
- **Problem Solving**: Define a clear goal, set a solvable sub-problem, and iterate.
- **Critical Thinking**: Beyond logic and statistics, it requires asking unexplored questions and digging for root causes.
- **Independent Research**: Independent does not mean alone; it means taking ownership of questions and seeking help strategically.
- **Idea Generation**: Find an interesting area, cite relevant papers, and continuously ask "What would happen if I tried X?".
- **Research Taste**: Use historical context (e.g., Turing Award citations) to gauge what is important versus what is noise.

#### AI and Scientific Musing
- **AI**: A rapidly evolving field covering machine translation, speech recognition, and large language models (LLMs). Building AI systems involves the end-to-end management of data pipelines, model training, evaluation, and deployment.
- **Science as Model Building**: Scientific progress shifts from absolute "truth-finding" to building models that explain observations.
- **The Limits of Correlation**: While research often starts by proving correlations, the search for underlying mechanisms is the path to causality.

### The Philosophy of Open Source
- **Transparency and Collaboration**: Open source is a fundamental driver of modern technology, allowing for global collaboration and rapid iteration.
- **Community Contribution**: Giving before taking—whether through code, documentation, or feedback—strengthens the ecosystem.

Related Topics:
- [[Work]]
- [[Learning]]
- [[Stoicism]]
- [[Economics]]
