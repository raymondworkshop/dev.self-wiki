---
title: Notes on Programming Languages
last_updated: '2026-05-26T16:54:20.267200'
description: A collection of technical notes covering programming concepts (recursion,
  tail-calls) and modern development environment setup (pipenv, module reloading).
level: 1
tags:
- topic/programming
- topic/workflow
- type/principle
alias: Notes on Programming Languages
---

> This entry compiles technical notes regarding recursion, tail-call optimization, and modern Python environment management using pipenv. It serves as a technical reference point for computational concepts and development workflows.



### Distillation (2026-05-26) - source: [[../raw/diary/2023-10-06-programming-languages.md]]
**Recursion & Stack Management:**
- Recursion can be elegantly implemented using tail-recursive calls, which allow the call stack to reuse space by popping the caller before the callee executes.

**Development Environment Management (Python 3):**
- **Reloading Modules:** Use `importlib` or IPython's `%autoreload` for dynamic module reloading during development.
- **Virtual Environments:** `pipenv` provides a streamlined workflow for setting up, installing dependencies, and activating isolated Python environments:
    - New Project: `pipenv --python 3.6`
    - Install: `pipenv install`
    - Locate Venv: `pipenv --venv`
    - Shell: `pipenv shell`
    - Uninstall All: `pipenv uninstall --all`

*(Note: The original entry contained a deleted section regarding PYTHONPATH configuration, which is omitted here for clarity.)*

**References:**
- [How to Design Programs, 2nd](https://htdp.org/2018-01-06/Book/index.html)
- [Fluent Python, 2nd](https://book.douban.com/subject/34990079/)


## Evolution


## Backlinks


## Sources
- [[../raw/diary/2023-10-06-programming-languages.md]]
