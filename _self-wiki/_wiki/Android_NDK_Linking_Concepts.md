---
last_updated: 2024-05-20T00:00:00Z
title: Android NDK Linking Concepts
description: Technical notes regarding the use of Android NDK, focusing on the build process and the concepts of linking (static vs. dynamic).
tags: [type/principle, work, technical]
---

> This document synthesizes technical notes on building applications using the Android NDK, specifically detailing the roles of Android.mk, Application.mk, and the low-level concepts of linking. It contrasts static and dynamic linking methods.

## Evolution
- Initial notes from 2016 regarding the technical implementation details of NDK builds.

## Content
### Android NDK Build Process
- **Android.mk**: Used to define properties specific to individual modules or libraries.
- **Application.mk**: Defines properties applicable to all modules used by the application.
- **ndk-build**: The build toolchain utilized for the compilation process.

### Linking Concepts
Linking is the process that concatenates compiled blocks and determines their run-time locations. This involves two critical steps:
1. **Symbol Resolution**: A symbol table associates each global symbol (functions and global variables) with a unique symbol definition.
2. **Relocation**: Memory locations are associated with each symbol definition, and then all sections of the same type are merged into a new aggregate section. Relocation symbol references are updated to point to the correct run-time addresses.

#### Linking with Static Libraries
- Related functions can be compiled into separate object modules and packaged into a single static library file.
- At link time, the linker copies only the object modules referenced by the program (via symbol resolution).
- **Advantages**: Requires periodic maintenance and updating of static libraries.
- **Caveat**: At run time, the code for functions like I/O functions is duplicated in the text segment of each running process.

#### Dynamic Linking with Shared Libraries
- A single copy of the `.text` section of a shared library can be shared across different running processes in memory.
- The basic idea is to complete the linking process (code and data) dynamically when the program is loaded, after the executable file has been created with relocation and symbol table information.

## Backlinks
<!-- BEGIN BACKLINKS -->
- **Mentioned in**: [[self-wiki/raw/diary/2016-03-31-notes-on-android-sdk-dev.md]]
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/diary/2016-03-31-notes-on-android-sdk-dev.md]]