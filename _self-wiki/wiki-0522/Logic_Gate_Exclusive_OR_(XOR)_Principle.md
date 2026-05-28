---
title: 'Logic Gate: Exclusive OR (XOR) Principle'
last_updated: '2026-05-20T20:54:35.573055'
description: A foundational computer science concept detailing the XOR operation,
  its mathematical equivalence to addition modulo 2, and its practical applications
  in error detection and encryption.
level: 2
tags:
- CS_Theory
- type/principle
- Logic
- Cryptography
alias: XOR 逻辑门
---

> XOR functions as addition modulo 2, where the result is true if and only if an odd number of inputs are true. This property makes it invaluable in cryptography for reversible bit-flipping operations and parity checking.



### Distillation (2026-05-20) - source: [[../raw/diary/2015-10-07-logicgate.md]]
**Exclusive OR (XOR) Principle**

XOR is mathematically equivalent to addition modulo 2 ($\text{XOR} \equiv 	ext{Addition Modulo 2}$). If $p_1, p_2, \dots, p_n$ are inputs, the result is true if and only if an odd number of inputs are true.

**Applications:**
1. **Cryptography:** Used with a mask to reversibly 'flip' bits during encryption/decryption.
2. **Parity Check:** Serves as a checksum to verify if an odd or even number of bits have been flipped during transmission.

**Traceability:**
*   *Mathematical Basis:* $\sum p_i \pmod{2}$ (Source: [[diary/2015-10-07-logicgate.md]])
*   *Application Context:* Bit manipulation in reversible operations (Source: [[diary/2015-10-07-logicgate.md]])


## Evolution


## Backlinks


## Sources
- [[../raw/diary/2015-10-07-logicgate.md]]
