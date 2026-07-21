---
title: Technical Application of Linking and Symbol Resolution
last_updated: '2026-05-20T20:49:56.171110'
description: A technical breakdown of the build process for Android applications utilizing
  the NDK, covering the roles of Android.mk, Application.mk, and the low-level linking
  stages.
level: 1
tags:
- topic/software_engineering
- topic/low_level_computing
- type/synthesis
alias: Notes on Android SDK dev
---

> This note details the technical processes involved in building software using the Android NDK, specifically focusing on how C/C++ code is integrated into a shared library application. The concepts of linking, symbol resolution, and relocation are crucial for creating executable binaries from compiled modules.



### Distillation (2026-05-20) - source: [[../raw/diary/2016-03-31-notes-on-android-sdk-dev.md]]
## Android NDK Build Process

- **Android.mk**: Used to define properties specific to individual compiled modules or libraries.
- **Application.mk**: Defines properties applicable across all modules used by the application.
- **ndk-build**: The build toolchain utilized for compilation.

### Linking Mechanics
Linking is the process of concatenating compiled blocks and determining their runtime locations.

1. **Symbol Resolution**: The linker uses a symbol table (.symtab) to map each global symbol (functions/variables) to its unique definition.
2. **Relocation**: This step associates a memory location with each symbol definition and adjusts references to point to the correct runtime addresses after merging sections of the same type into a new aggregate section.

### Linking Strategies
- **Static Linking**: Related functions are compiled into object modules and packaged into a static library. The linker copies only the referenced object modules during the link time.
    - *Advantage*: Allows for the bundling of necessary code.
    - *Caveat*: Code duplication occurs in the text segment of each running process.
- **Dynamic Linking (Shared Libraries)**: A single copy of the shared library's .text section can be utilized by multiple running processes in memory.

**Core Idea**: The executable file is created by establishing the relocation and symbol table information, and the final code/data linking is completed dynamically upon program load.


## Evolution


## Backlinks


## Sources
- [[../raw/diary/2016-03-31-notes-on-android-sdk-dev.md]]
