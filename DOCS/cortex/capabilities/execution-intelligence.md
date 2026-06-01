# Execution Intelligence Capability

Execution intelligence identifies how execution reality deviates from plan over time.

## Capability Set

- blocker propagation analysis,
- ownership instability detection,
- execution drift detection,
- delivery continuity gaps,
- coordination bottleneck mapping,
- dependency fragility scoring.

## Required Models

- **Continuity:** stable actor/artifact/initiative linkage across tools.
- **Temporal:** state transition timelines and change-point detection.
- **Reasoning:** deterministic heuristics first, bounded synthesis second.

## Trust Requirements

- each insight tied to concrete evidence windows,
- inferred risk explicitly labeled as inferred,
- confidence calibrated by evidence density and consistency.

## Typical Workflow

1. reconstruct execution timeline for initiative window,
2. compute transitions in ownership/state/dependencies,
3. detect anomalous propagation or drift,
4. surface bottlenecks with provenance chain,
5. compare against replay baselines for stability.

## Architectural Dependencies

Phases 01-09 with strong requirements on 04 (identity), 05 (graph), 06 (memory), 07 (reasoning), 08 (retrieval), 09 (synthesis).

**Execution scope (materialization, not intelligence):**

| Layer | Role | V1 |
|-------|------|-----|
| **Declared Domain** | Cross-tool rollup of declared initiative/project + momentum | Yes |
| **Emergent Domain** | Undeclared concerns (Authentication, Hiring, …) | Future |
| **Execution Intelligence** | Risk, drift, delivery on scope | Future |

See [`execution-scope-architecture.md`](../execution-scope-architecture.md) and [`declared-domains-v1-plan.md`](../declared-domains-v1-plan.md).
