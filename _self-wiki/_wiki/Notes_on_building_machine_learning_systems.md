---
title: Notes on building machine learning systems
last_updated: '2026-05-21T00:48:23.670065'
description: A procedural guide detailing the lifecycle stages of an ML project, from
  requirements gathering to production deployment, including the role of human oversight
  and A/B testing.
level: 1
tags:
- type/principle
- process/development
- topic/technology
- topic/MLOps
- machine_learning
- type/synthesis
alias: Notes about machine learning
---

> This document outlines a structured, iterative workflow for developing ML systems, emphasizing the critical need to define the business objective and success metrics before prototyping. The process moves from initial goal definition through prototyping, rigorous testing, and finally to production deployment involving data and analytics teams.

### Distillation (2026-05-21) - source: [[../raw/diary/tech/2019-07-17-machine-learning-systems.md]]
**Phase 1: Requirements Elicitation**
*   **Business Objective**: Must clearly define how the company expects the model to be used and benefit.
*   **Goal Setting**: Define the specific question or goal the ML problem aims to answer.
*   **Success Metrics**: Define and measure success using tangible business metrics (e.g., increased profit, decreased losses).

**Phase 2: Prototyping Loop**
*   Acquire data and build a working prototype.
*   Iterative Cycle: Analyze mistakes $\rightarrow$ Collect/diff data $\rightarrow$ Slightly change task formulation.
*   Human-in-the-Loop: Consider how algorithms affect response time or cost.

**Phase 3: Productionization**
*   Data Analytics Teams $\rightarrow$ Production Teams.
*   Deployment requires reimplementing the solution for robustness and scalability.
*   Testing Protocol: Offline evaluation followed by online A/B testing.

### Distillation (2026-05-21) - source: [[../raw/diary/tech/2019-04-30-deep-learning.md]]
## YAML Front Matter
`last_updated`: 2019-04-30
`title`: Notes about machine learning
`description`: Initial ingestion of ML concepts.

**## Core Components**

*   **特徵工程 (Feature Engineering)**: TODO
*   **模型評估 (Model Evaluation)**: TODO
*   **經典算法 (Classic Algorithms)**:
    *   Supervised Learning
    *   Unsupervised Learning
    *   Model evaluation and improvement
    *   Pipeline
*   **神經網絡 (Neural Networks)**: Deep Learning
*   **生成式对抗网络 (GAN)**: GANs

**## Traceability**
(Source: [[diary/tech/2019-04-30-deep-learning.md]])


## Evolution


## Backlinks


## Sources
- [[../raw/diary/tech/2019-04-30-deep-learning.md]]
- [[../raw/diary/tech/2019-07-17-machine-learning-systems.md]]
