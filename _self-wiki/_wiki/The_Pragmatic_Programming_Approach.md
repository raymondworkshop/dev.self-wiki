---
last_updated: 2024-05-29T12:00:00Z
title: The Pragmatic Programming Approach
description: Synthesizes core principles from "The Pragmatic Programmer" regarding requirements gathering, problem-solving, and the role of tools in knowledge work.
tags: [type/principle, work, habit]
---

> This document outlines a pragmatic approach to software development and complex problem-solving, emphasizing the importance of understanding the 'why' behind requirements, mastering fundamental tools, and approaching debugging as pure problem-solving. It stresses that abstractions endure longer than specific details.

## Evolution
- Initial concepts regarding requirements gathering and the role of tools are being formalized into a cohesive working philosophy.

## Content

### Chapter 7: Before the Project - Requirements Digging
When gathering requirements, the focus must shift from merely documenting *what* is needed to understanding *why* it is needed.

*   **General Statement vs. Policy Example**: The requirement itself should be the general statement, while specific implementation details serve as policy examples.
*   **Discovering Underlying Reasons**: It is crucial to uncover the root cause or the underlying business problem driving a particular need, rather than just documenting the surface-level solution.
    *   This involves documenting the *reasons* behind the requirements.
    *   The developer's role is to solve the *business problem*, not just meet the stated, surface-level requirements.
*   **Use Case Conceptualization**: Proposing use cases serves as a common ground for discussion among developers, end-users, and project sponsors.
*   **Requirements as Needs**: Requirements must accurately reflect the genuine business need.
    *   They must capture the underlying semantic invariants, while specific implementations are documented as policy.
    *   **Abstraction is key**: Abstractions possess greater longevity than granular details.

### The Pragmatic Approach
*   The evaluation of duplication and orthogonality is vital in any system design.

### The Basic Tools - Tools Amplify Your Talent
*   **Invest in Your Toolbox**: Dedication to one's foundational tools is paramount.
*   **Plain Text as Standard**: Our base material is knowledge. This knowledge must be expressed consistently across designs, implementations, tests, and documentation. Plain text remains the most persistent format for storing knowledge.
*   **Power Editing**: One must achieve effortless manipulation of text using a single, well-mastered editor for all editing tasks.
*   **Debugging as Problem Solving**: Debugging is fundamentally problem-solving, and it should be attacked as such.
    *   **Visualize Data**: Gain a clear view of the data currently in operation.
    *   **Tracing**: Follow the state of a program or data structure over time.
    *   **Prove, Don't Assume**: Do not assume; prove your hypotheses about the system's state and how to improve it.
    *   **Master One Language**: Achieve mastery in one text manipulation language.

## Backlinks
<!-- BEGIN BACKLINKS -->
- **Mentioned in**: [[Self_Wiki_Operating_Manual.md]] (Contextual application of principles)
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/diary/notes/2018-05-11-the-pragmatic-programming.md]]