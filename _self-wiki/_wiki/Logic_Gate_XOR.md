---
last_updated: 2024-05-29T12:00:00Z
title: Logic Gate XOR
description: Explores the XOR operation, its application in cryptography, and its equivalence to addition modulo 2.
tags: [type/principle, work, cognitive_model]
---

> The XOR operation is a fundamental binary operation used in computing, notably in cryptography due to its ability to reversibly 'flip' bits. Mathematically, it functions identically to addition modulo 2, where the result is true if and only if an odd number of inputs are true.

## Evolution
- Initial concept derived from a specific technical note regarding binary operations. The current entry formalizes its mathematical properties and practical applications.

## Content
### Exclusive OR (XOR)
XOR is a binary operation defined by the condition that the result is true (1) if and only if the inputs are different.

**Applications and Properties:**

1.  **Cryptography:** XOR is heavily utilized in cryptography because it allows bits to be 'flipped' using a mask through a reversible operation.
2.  **Parity Check/Checksum:** It can be used to perform a parity check, acting as a simple checksum to detect if any bit has been flipped.
3.  **Mathematical Equivalence:** For $n$ variables ($p_1, p_2, \dots, p_n$), the expression $p_1 \oplus p_2 \oplus \dots \oplus p_n$ is true if and only if the number of variables set to true (1) is odd. This is equivalent to addition modulo 2:
    $$\text{XOR} \equiv \text{Addition Modulo 2}$$
    $$\text{p}_1 \oplus \text{p}_2 \oplus \dots \oplus \text{p}_n \iff (\text{p}_1 + \text{p}_2 + \dots + \text{p}_n) \pmod{2}$$

### Key Takeaways
*   **Flipping Bits:** XOR provides a mechanism to invert bits when combined with a mask.
*   **Odd Count:** The operation sums the inputs modulo 2, making it sensitive to the parity (odd/even count) of '1's.

## Backlinks
<!-- BEGIN BACKLINKS -->
- **Mentioned in**: [[Self-Wiki Operating Manual]] (Conceptual basis for structured knowledge)
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/diary/2015-10-07-logicgate.md]]