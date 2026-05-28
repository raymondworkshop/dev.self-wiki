---
title: Notes on Programming Languages and Computational Models
last_updated: '2026-05-26T16:53:32.514512'
description: A technical deep dive into programming language execution models, Python's
  object behavior, and memory management concepts (sequences, generators, hash tables).
level: 1
tags:
- topic/programming
- topic/memory_management
- type/principle
- topic/computer_science
alias: Notes on Programming Languages
---

> This entry compares different computational models, specifically detailing the execution flow of an interpreter (Parse -> AST -> Eval) and contrasting Python's Data Model with low-level memory management concepts. It explores the efficiency trade-offs between mutable/immutable sequences, hash tables, and generators.



### Distillation (2026-05-26) - source: [[../raw/diary/2023-10-06-programming-languages.md]]
### Interpreter Execution Flow
Program execution follows a standard pipeline: Parse $\rightarrow$ Abstract Syntax Tree (AST) $\rightarrow$ Evaluate $\rightarrow$ Result.

### Python Data Model & Object Behavior
Leveraging Python's special methods allows objects to behave like built-in types, enabling 'Pythonic' expression.

#### Data Structures Comparison
- **Flat Sequences (str, bytes, array.array)**: Store values directly in memory, offering high compactness for numeric data (e.g., `array.array` with packed bytes).
- **Container Sequences (list, tuple, deque)**: Hold references to objects.
    - **List**: Mutable, supports mixed types, requires copying for safety (`list(t)` creates a new copy).
    - **Tuple**: Immutable, passes references efficiently (`tuple(t)` returns the same object), uses less memory than a list for fixed data.
- **Hash Tables (dict, set)**: Provide high-performance lookups but are inherently sparse and less space-efficient than contiguous arrays.

#### Functions as Entities
Functions can be treated as first-class objects (like integers or strings), enabling functional programming paradigms. Decorators (`@deco`) wrap functions, allowing modification of behavior without altering the core logic.

#### Iteration and Generators
- **Iterable**: An object with a `__iter__()` method that produces an iterator.
- **Iterator**: An object with a `__next__()` method that yields individual items.
- **Generator**: A function utilizing `yield` that automatically implements the iterator protocol. `yield` pauses execution and saves the local state, allowing resumption upon the next call.


## Evolution


## Backlinks


## Sources
- [[../raw/diary/2023-10-06-programming-languages.md]]
