# Software Architecture: The Socratic Mirror (LLM-Native)

## 1. Philosophy: Thin Harness, Fat Skills
This project follows the "Thin Harness, Fat Skills" design pattern. Intelligence is pushed "up" into declarative skill definitions (GEMINI.md), while execution is pushed "down" into deterministic tooling (Python scripts).

### The Three Layers
1.  **Skills Layer (The "Fat" Part)**: 
    - **Location**: `GEMINI.md` and LLM Prompts.
    - **Function**: Encodes judgement, Socratic process, and domain knowledge. 
    - **Logic**: Latent, non-deterministic, and reasoning-heavy.
2.  **Harness Layer (The "Thin" Part)**: 
    - **Location**: `scripts/orchestrator_v2.py`, `scripts/sync_wiki.py`.
    - **Function**: The "glue" that runs the LLM in loops, manages context windows, and handles I/O.
    - **Logic**: Simple orchestration and error handling.
3.  **Deterministic Layer (The "Trust" Part)**:
    - **Location**: `scripts/models.py`, `scripts/config.py`, `scripts/backliner.py`.
    - **Function**: File hashing, directory structure enforcement, graph consistency, and unit tests.
    - **Logic**: Absolute reliability. Same input = Same output.

---

## 2. Core Components

### A. The Distiller (Raw -> Synthesis -> Principle)
- **Input**: Level 0 (Raw) markdown files.
- **Process**: 
    1.  **Diarization**: LLM analyzes raw input for semantic "nuggets".
    2.  **Clustering**: Match nuggets to existing Level 1 (Synthesis) or Level 2 (Principle) files.
    3.  **Update**: Surgical merge into wiki files using the `WikiPage` model.
- **Output**: Updated `.md` files in `self-wiki/wiki/`.

### B. The Socratic Auditor
- **Function**: Scans the wiki for "Cognitive Friction".
- **Tasks**:
    - Identify contradictions between new entries and old principles.
    - Flag "Red Links" (missing topics).
    - Detect "Stale Wisdom" (principles not updated in 6+ months).

### C. The Backliner (Graph Engine)
- **Function**: Maintains the bi-directional links between topics.
- **Format**: `<!-- BEGIN BACKLINKS -->` blocks.

---

## 3. Data Flow
`raw/` (Read-only) 
  -> `Orchestrator` (Check Hashing)
    -> `Distiller` (LLM Reasoning)
      -> `Models.WikiPage` (Schema Enforcement)
        -> `wiki/` (Final Output)
          -> `Auditor` (Validation)

---

## 4. Testing Strategy

### A. Compliance Testing (Deterministic)
- Validates YAML front matter.
- Ensures required sections (Evolution, Backlinks, Sources) exist.
- Checks Socratic Summary length and tone.

### B. Functional Testing (Integration)
- **Mock Distillation**: Provide a raw file and verify the LLM correctly identifies the target wiki page and extracts the source link.
- **Contradiction Detection**: provide two contradicting raw files and verify the Auditor flags them.

### D. Fidelity Guardrails (Anti-Hallucination)
To ensure the wiki reflects the **Raw Truth** and not AI "creativity", the system implements:
1.  **Direct Quotation**: AI is encouraged to use blockquotes `> ` for direct evidence from raw files.
2.  **Explicit Tagging**: Any pattern recognized by the AI that is not literal in the source must be tagged with `[AI Synthesis]`.
3.  **Traceability Verification**: The `Auditor` compares wiki claims against the specific `[[raw-source]]` linked. If a claim in the wiki cannot be found in the linked source, it is flagged as a "Hallucination Risk".
