> **SUPERSEDED — NON-NORMATIVE**  
> This document predates **Phase 05 OCTS** (Organizational Continuity Traversal Substrate). It **MUST NOT** be used for implementation, architecture decisions, or API design.  
> **Normative specifications:** [`DOCS/cortex/05-traversal/`](../05-traversal/) — entrypoint [`phase-05-normative-index.md`](../05-traversal/phase-05-normative-index.md).  
> **Program / steps:** [`DOCS/cortex/MASTER_TRACKER.md`](../MASTER_TRACKER.md) (Phase 05, Steps 1–26).

---

# Organizational Graph Layer Architecture

## Input Contracts
- Resolved entities
- Canonical relations
- Temporal transition artifacts

## Output Contracts
- Temporal graph edges
- Lineage paths
- State transition adjacency

## Allowed Logic
- Contract validation and schema version checks.
- Deterministic transformation inside declared ownership.
- Confidence annotation only when phase contract requires it.

## Forbidden Logic
- No summarization output formatting
- No AI-generated truth assertions
- No source connector logic

## Dependency Boundary
This phase depends only on upstream-adjacent contracts and shared schema definitions. Direct dependency on non-adjacent phase internals is forbidden.
