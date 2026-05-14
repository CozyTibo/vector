> **SUPERSEDED — NON-NORMATIVE**  
> This document predates **Phase 05 OCTS** (Organizational Continuity Traversal Substrate). It **MUST NOT** be used for implementation, architecture decisions, or API design.  
> **Normative specifications:** [`DOCS/cortex/05-traversal/`](../05-traversal/) — entrypoint [`phase-05-normative-index.md`](../05-traversal/phase-05-normative-index.md).  
> **Program / steps:** [`DOCS/cortex/MASTER_TRACKER.md`](../MASTER_TRACKER.md) (Phase 05, Steps 1–26).

---

# 05-graph Technical Decisions

## Required Decisions Before Implementation
- edge type taxonomy and directionality
- temporal validity encoding for edges
- superseded edge retention policy
- lineage traversal depth constraints

## Decision Constraints
- Decisions must preserve deterministic replay semantics.
- Decisions must not violate phase ownership boundaries.
- Cross-phase impact requires ADR linkage and contract versioning.
