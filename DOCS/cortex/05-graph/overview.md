> **SUPERSEDED — NON-NORMATIVE**  
> This document predates **Phase 05 OCTS** (Organizational Continuity Traversal Substrate). It **MUST NOT** be used for implementation, architecture decisions, or API design.  
> **Normative specifications:** [`DOCS/cortex/05-traversal/`](../05-traversal/) — entrypoint [`phase-05-normative-index.md`](../05-traversal/phase-05-normative-index.md).  
> **Program / steps:** [`DOCS/cortex/MASTER_TRACKER.md`](../MASTER_TRACKER.md) (Phase 05, Steps 1–26).

---

# Organizational Graph Layer Overview

## Why This Phase Exists
This phase isolates a specific transformation responsibility in the Cortex cognition pipeline so downstream intelligence remains deterministic, replayable, and explainable.

## Responsibilities
- Temporal relationship graph construction
- Decision/dependency/blocker/ownership edge typing
- Lineage traversal primitives

## Non-Responsibilities
- No summarization output formatting
- No AI-generated truth assertions
- No source connector logic

## Ownership Boundary
This phase owns only its contract outputs and may not bypass adjacent layers.
