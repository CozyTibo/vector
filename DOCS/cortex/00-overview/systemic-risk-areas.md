# Systemic Risk Areas

## Purpose
Identify high-risk architectural failure modes and define prevention and governance safeguards.

## Ontology Drift
- Symptoms:
  - conflicting definitions for decision/concern/ownership.
- Causes:
  - uncontrolled term additions, connector-specific semantics leakage.
- Downstream effects:
  - inconsistent graph typing, retrieval confusion, synthesis contradiction.
- Prevention:
  - enforce `terminology-consistency.md` and `organizational-ontology.md`.
- Governance safeguards:
  - ontology review + architecture escalation for definition changes.

## Replay Corruption
- Symptoms:
  - replay outputs not comparable, unexplained divergence spikes.
- Causes:
  - missing version pinning, in-place mutation, broken replay isolation.
- Downstream effects:
  - memory inconsistency, untrustworthy reasoning evolution.
- Prevention:
  - strict replay metadata and supersession publication policy.
- Governance safeguards:
  - replay review mandatory for schema/inference changes.

## Provenance Loss
- Symptoms:
  - claims without evidence chains, missing input/source refs.
- Causes:
  - incomplete phase handoff contracts, ad hoc derived outputs.
- Downstream effects:
  - explainability failure and governance blind spots.
- Prevention:
  - mandatory provenance fields on all non-raw outputs.
- Governance safeguards:
  - provenance checklist gates and escalation.

## AI Boundary Erosion
- Symptoms:
  - AI suggestions treated as canonical truth.
- Causes:
  - relaxed confidence requirements, hidden inference usage.
- Downstream effects:
  - epistemic drift and non-reproducible behavior.
- Prevention:
  - deterministic-only zones and bounded AI contract enforcement.
- Governance safeguards:
  - AI-boundary review + ADR for scope expansions.

## Temporal Inconsistency
- Symptoms:
  - contradictory timelines, supersession ambiguity.
- Causes:
  - timestamp misuse, invalid ordering assumptions.
- Downstream effects:
  - broken historical reconstruction and causal analysis.
- Prevention:
  - enforce temporal precedence and validity windows.
- Governance safeguards:
  - temporal review for time semantics changes.

## Connector-Specific Leakage
- Symptoms:
  - tool-specific logic appears in canonical/reasoning assumptions.
- Causes:
  - connector overreach or schema shortcuts.
- Downstream effects:
  - reduced portability and cross-tool cognition failure.
- Prevention:
  - adapter-only connector policy.
- Governance safeguards:
  - phase boundary checks and connector philosophy enforcement.

## Graph Inconsistency
- Symptoms:
  - contradictory edge semantics, unstable relation meaning.
- Causes:
  - ontology drift, unresolved relation typing policy.
- Downstream effects:
  - invalid dependency and ownership reasoning.
- Prevention:
  - relation taxonomy governance and temporal validity constraints.
- Governance safeguards:
  - canonical + graph review for ontology/relation changes.

## Hidden Coupling
- Symptoms:
  - phase-local changes unexpectedly break downstream phases.
- Causes:
  - undocumented cross-phase dependencies.
- Downstream effects:
  - cascading failures, implementation gridlock.
- Prevention:
  - maintain `phase-dependency-graph.md` and contract dependency matrix.
- Governance safeguards:
  - mandatory cross-phase impact statement for Level 2+ changes.

## Semantic Duplication
- Symptoms:
  - duplicate terms or fields with different meanings.
- Causes:
  - ad hoc naming without field semantics governance.
- Downstream effects:
  - schema confusion and inconsistent implementation.
- Prevention:
  - field naming and terminology policy enforcement.
- Governance safeguards:
  - schema review and drift checklist contract checks.

## Conflicting Derived Memory
- Symptoms:
  - divergent memory projections for same evidence set.
- Causes:
  - stale compaction policies, replay lag, version mismatch.
- Downstream effects:
  - inconsistent retrieval and synthesis results.
- Prevention:
  - derived memory rebuild/version policy and replay monitoring.
- Governance safeguards:
  - replay + memory architecture review gates.
