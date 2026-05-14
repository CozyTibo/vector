> **SUPERSEDED — NON-NORMATIVE**  
> This document predates **Phase 05 OCTS** (Organizational Continuity Traversal Substrate). It **MUST NOT** be used for implementation, architecture decisions, or API design.  
> **Normative specifications:** [`DOCS/cortex/05-traversal/`](../05-traversal/) — entrypoint [`phase-05-normative-index.md`](../05-traversal/phase-05-normative-index.md).  
> **Program / steps:** [`DOCS/cortex/MASTER_TRACKER.md`](../MASTER_TRACKER.md) (Phase 05, Steps 1–26).

---

# 05-graph Open Questions

## Questions To Resolve
- Which edges are deterministic-only vs inferred-allowed?
- How are concurrent conflicting edges represented?
- What traversal guarantees are required for reasoning?

## Blockers
- Relation type registry not finalized
- Temporal validity model unresolved

## Resolution Rule
All blockers must be cleared before implementation kickoff for this phase.
