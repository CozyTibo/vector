> **SUPERSEDED — NON-NORMATIVE**  
> This document predates **Phase 05 OCTS** (Organizational Continuity Traversal Substrate). It **MUST NOT** be used for implementation, architecture decisions, or API design.  
> **Normative specifications:** [`DOCS/cortex/05-traversal/`](../05-traversal/) — entrypoint [`phase-05-normative-index.md`](../05-traversal/phase-05-normative-index.md).  
> **Program / steps:** [`DOCS/cortex/MASTER_TRACKER.md`](../MASTER_TRACKER.md) (Phase 05, Steps 1–26).

---

# 05-graph Risks

## Phase-Specific Risks
- edge explosion from unbounded relation generation
- cyclic dependency misclassification
- temporal edge conflicts after late-arriving events
- graph reads coupling to synthesis assumptions

## Mitigation Expectations
- Detect risk conditions through explicit telemetry.
- Preserve partial truthful outputs under degradation.
- Quarantine unsafe artifacts instead of silently dropping them.
