---
last_updated: 2024-05-20T12:00:00Z
title: Computer Systems Fundamentals
description: A technical overview of computer system concepts, including performance optimization, memory hierarchy, linking, and control flow.
tags: [type/synthesis, work, principle]
---

> This document synthesizes core concepts from computer systems programming, covering performance trade-offs, memory management hierarchies, and low-level software construction techniques like linking and exception handling. It provides a foundational understanding of how hardware and software interact to execute a program.

## Evolution
- Initial concepts were fragmented across various chapters (Ch5-Ch9) of the source material. This synthesis structures these concepts into a cohesive overview.

## Content

### Ch5: Optimizing Program Performance
Performance optimization involves balancing implementation ease against execution speed. Key considerations include:
- Selecting appropriate algorithms and data structures.
- Allowing the compiler to perform optimizations (e.g., reducing function calls, eliminating unnecessary memory references by introducing temporary variables).
- Profiling the program to identify bottlenecks.
- Understanding Amdahl's Law: performance gain is limited by the fraction of the program that cannot be parallelized or improved.

### Ch6: The Memory Hierarchy
Modern computing relies on bridging the gap between fast, expensive storage (CPU registers/cache) and slow, high-capacity storage (disk).
- **Storage Trade-off**: Technologies balance price against access time (e.g., SRAM vs. DRAM vs. SSD).
- **Hierarchy**: Systems organize memory to exploit **locality**.
    - **Temporal Locality**: Reusing the same data object multiple times.
    - **Spatial Locality**: Accessing nearby memory locations sequentially (stride 1).
- Programs with good locality access data primarily from fast cache memory, leading to much faster execution compared to those constantly accessing main memory.

### Ch7: Linking
Linking combines compiled code into a runnable executable.
- **Concatenation**: The linker joins object modules and resolves run-time locations.
- **Symbol Resolution**: The linker maps references to global symbols (functions/variables) to their unique definitions.
- **Relocation**: The linker assigns specific memory addresses to each symbol definition.
- **Static Linking**: Object modules are copied into the final executable at link time. Advantage: self-contained. Disadvantage: code duplication across processes.
- **Dynamic Linking**: The executable contains references, and the actual code/data is loaded into memory only when the program runs, allowing multiple processes to share a single copy of a library's text segment.

### Ch8: Exceptional Control Flow (ECF)
ECF manages abrupt changes in processor state that require control transfer.
- **Control Transfer**: Moving from address $a_k$ to $a_{k+1}$.
- **Exception**: An abrupt control flow change triggered by a change in the processor's state (the event).
    - **Interrupt Handling**: Responding to I/O device events.
    - **Trap Handling**: System calls acting as a user-to-kernel interface.
    - **Fault Handling**: Recovering from error conditions.
    - **Abort Handling**: Unrecoverable errors.
- **Process**: An independent logical flow with its own private address space. Concurrent flows overlap in time.

### Network Programming
- Client-server connections are often full-duplex and reliable.
- Concurrent servers can be based on processes or threads.
- Concurrent programming involves overlapping execution in time, achieved via processes, I/O multiplexing, or threads.

## Evolution
- This page represents the first structured attempt to synthesize disparate technical notes into a unified, navigable knowledge base, adhering to the strict provenance tracking required by the Self-Wiki Operating Manual.

## Backlinks
<!-- BEGIN BACKLINKS -->
- **Mentioned in**: [[Self_Wiki_Operating_Manual.md]]
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/diary/2017-05-16-an-overview-of-computer-system.md]]