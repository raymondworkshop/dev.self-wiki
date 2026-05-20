---
last_updated: 2024-05-20T00:00:00Z
title: Machine Learning System Development Lifecycle
description: A structured approach to developing, prototyping, and deploying ML solutions, moving from initial business objective to production-ready system.
tags: [type/principle, work, synthesis]
---

> This document outlines the necessary stages for successfully translating a machine learning concept into a functional, production-grade system. It emphasizes the iterative loop between prototyping, rigorous testing, and real-world deployment feedback.

## Evolution
- Initial notes focused on the technical steps of ML modeling.
- Current synthesis integrates the necessary business context (objective definition, success metrics) and deployment phases (prototyping vs. production) into a cohesive lifecycle model.

## Content
### Phase 1: Defining the Problem (Digging for Requirements)
The initial phase must establish clear boundaries and success criteria before technical work begins.
*   **Business Objective:** What is the ultimate business goal? How is the company expecting the model to provide value or benefit?
*   **Goal Definition:** Precisely define the question or goal the ML model is intended to answer.
*   **Success Metrics:** Define and quantify how success will be measured (e.g., increased profit, decreased loss).

### Phase 2: Prototyping (The Iterative Loop)
This phase involves building a working model to test feasibility.
*   **Development:** Acquire necessary data and build a functional prototype.
*   **Evaluation Loop:** This phase is inherently iterative:
    1.  Analyze model mistakes.
    2.  Collect more or different data.
    3.  Slightly adjust the task formulation based on findings.
*   **Human Integration:** Consider the role of humans in the loop, as algorithms might affect response time or operational cost.

### Phase 3: Productionization (From Prototype to Production)
Moving beyond the prototype requires robust engineering practices to ensure scalability and reliability.
*   **Data Analytics Teams:** Involved in the transition phase.
*   **Production Teams:** Responsible for reimplementing the solution into a robust, scalable system.
    *   Offline evaluation.
    *   Online testing using A/B testing.

## Backlinks
<!-- BEGIN BACKLINKS -->
- **Evolved from**: [[self-wiki/raw/diary/tech/2019-07-17-machine-learning-systems.md]]
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/diary/tech/2019-07-17-machine-learning-systems.md]]