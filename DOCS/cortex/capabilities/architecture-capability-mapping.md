# Architecture-Capability Mapping

This map ties each capability to required architecture guarantees.

## Mapping Dimensions

For each capability we track:

- required phases,
- required storage/query guarantees,
- required replay guarantees,
- required temporal guarantees,
- required provenance guarantees,
- required reasoning maturity.

## Capability Trace Map

### Organizational Search

- **Phases:** 01-08.
- **Storage/query:** provenance + time-indexed retrieval over canonical/graph layers.
- **Replay:** stable identifiers and version-aware retrieval views.
- **Temporal:** as-of and interval semantics.
- **Provenance:** source refs must be first-class in search results.
- **Reasoning maturity:** low; mostly retrieval + deterministic ranking.

### Execution Intelligence

- **Phases:** 01-09.
- **Storage/query:** dependency/ownership traversal at org scale.
- **Replay:** compare execution inferences across replay generations.
- **Temporal:** drift/change-point detection on execution state.
- **Provenance:** each inferred bottleneck linked to evidence windows.
- **Reasoning maturity:** medium deterministic + bounded synthesis.

### Incident Analysis

- **Phases:** 01-09.
- **Storage/query:** cross-tool timeline reconstruction queries.
- **Replay:** capability to recompute incident views after schema/model changes.
- **Temporal:** precise event ordering + state transitions.
- **Provenance:** distinguish observed sequence vs inferred causality.
- **Reasoning maturity:** medium-high with strict non-speculative boundaries.

### Onboarding Intelligence

- **Phases:** 01-08.
- **Storage/query:** efficient retrieval of initiative/decision history.
- **Replay:** historical explanations remain traceable post-replay.
- **Temporal:** long-horizon continuity across staffing/tool changes.
- **Provenance:** each onboarding narrative section evidence-backed.
- **Reasoning maturity:** medium synthesis with citation constraints.

### Strategic Analysis

- **Phases:** 01-09.
- **Storage/query:** pattern mining over initiative and dependency history.
- **Replay:** trend calculations resilient to backfills/reprocessing.
- **Temporal:** multi-quarter trend windows and cohort comparisons.
- **Provenance:** strategic claims expose uncertainty and data coverage.
- **Reasoning maturity:** high caution; no omniscience assumptions.

### Delivery Reconstruction

- **Phases:** 01-07.
- **Storage/query:** artifact/decision/dependency lineage traversals.
- **Replay:** regenerate delivery chain after ontology evolution.
- **Temporal:** implementation evolution snapshots.
- **Provenance:** trace every chain edge to source events.
- **Reasoning maturity:** mostly deterministic.

### Decision Lineage

- **Phases:** 01-07.
- **Storage/query:** decision-to-artifact and decision-to-outcome graph edges.
- **Replay:** stable decision identity through reprocessing.
- **Temporal:** decision emergence/change/reversal timeline.
- **Provenance:** explicit confidence and ambiguity for inferred links.
- **Reasoning maturity:** medium deterministic + bounded inference.

### Dependency Intelligence

- **Phases:** 01-09.
- **Storage/query:** dependency graph plus propagation simulation queries.
- **Replay:** compare fragility metrics across runs.
- **Temporal:** evolving dependency topology over time.
- **Provenance:** show evidence and uncertainty for each dependency edge.
- **Reasoning maturity:** medium-high.

### Initiative Continuity

- **Phases:** 01-07.
- **Storage/query:** continuity stitching across renamed/split initiatives.
- **Replay:** stable continuity assignments with version lineage.
- **Temporal:** initiative lifecycle model (birth/split/merge/retire).
- **Provenance:** continuity decisions explainable and revisable.
- **Reasoning maturity:** medium.

### Operational Debugging / Ambiguity / Replay Analysis

- **Phases:** 01-10.
- **Storage/query:** operator-accessible phase-level diagnostics + drill-down.
- **Replay:** first-class replay orchestration and diff inspection.
- **Temporal:** ability to inspect system behavior at past points.
- **Provenance:** ambiguity and confidence displayed in admin surfaces.
- **Reasoning maturity:** low-medium; mostly investigation tooling.

### Historical Organizational Reconstruction

- **Phases:** 01-09.
- **Storage/query:** snapshot materialization and topological reconstruction at scale.
- **Replay:** replay-safe historical state regeneration.
- **Temporal:** strong period-aware state modeling.
- **Provenance:** explicit observed vs inferred historical structure.
- **Reasoning maturity:** medium-high with strict uncertainty controls.
