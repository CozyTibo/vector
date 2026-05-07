# Invariant Enforcement Matrix

## Purpose
This document explains why each invariant exists, what fails if it is violated, and which system assumptions depend on it.

## Invariant: Raw Immutability
- Why it exists: preserves source truth, replay baseline, and forensic auditability.
- What breaks if violated:
  - replay no longer deterministic from trusted baseline,
  - provenance chains become unverifiable,
  - historical reconstruction collapses.
- Phase dependencies:
  - direct: `01-ingestion`, `02-raw-store`
  - indirect: all downstream stages.
- Schema dependencies:
  - `schemas/contracts.md` immutable fields
  - `schemas/field-semantics.md` mutability rules
- Replay dependencies:
  - full and targeted replay guarantees.
- AI dependencies:
  - AI restricted from raw mutation.
- Lifecycle dependencies:
  - source event lifecycle and supersession model.

## Invariant: Provenance Continuity
- Why it exists: enables explainability and evidence traceability end-to-end.
- What breaks if violated:
  - synthesis claims become non-auditable,
  - confidence loses meaning,
  - governance cannot validate decisions.
- Phase dependencies:
  - all phase handoffs.
- Schema dependencies:
  - `provenance.*` and `supporting_evidence_refs`.
- Replay dependencies:
  - replay comparison cannot validate divergence cause.
- AI dependencies:
  - inferred outputs require evidence trace.
- Lifecycle dependencies:
  - inference and synthesis lifecycles.

## Invariant: Deterministic-First
- Why it exists: creates stable, testable base behavior before probabilistic inference.
- What breaks if violated:
  - system behavior becomes non-reproducible,
  - replay validation weakens,
  - architectural authority drifts to prompts.
- Phase dependencies:
  - mandatory in `01-06`, constrained in `07-09`.
- Schema dependencies:
  - `extraction_version`, `processor_version`.
- Replay dependencies:
  - deterministic output stability requirements.
- AI dependencies:
  - AI invocation only after deterministic extraction and ambiguity mark.
- Lifecycle dependencies:
  - extraction and canonicalization lifecycles.

## Invariant: Canonical Tool-Agnostic Memory
- Why it exists: enables cross-tool cognition and unified ontology.
- What breaks if violated:
  - tool-specific silos return,
  - graph reasoning becomes inconsistent,
  - retrieval semantics fragment by connector.
- Phase dependencies:
  - producer: `03-canonical`
  - consumers: `04-09`.
- Schema dependencies:
  - canonical ids and relation type contracts.
- Replay dependencies:
  - canonical layer must regenerate under mapping version changes.
- AI dependencies:
  - AI cannot redefine canonical taxonomy directly.
- Lifecycle dependencies:
  - canonicalization and graph lifecycles.

## Invariant: Temporal Integrity
- Why it exists: decision evolution and causal reconstruction depend on reliable chronology.
- What breaks if violated:
  - ownership evolution cannot be reconstructed,
  - supersession chains become ambiguous,
  - causal analysis misorders events.
- Phase dependencies:
  - strongest in `05-09`, but depends on upstream timestamps.
- Schema dependencies:
  - `occurred_at`, `observed_at`, `processed_at`, `inferred_at`,
  - `effective_from`, `effective_to`.
- Replay dependencies:
  - replay cannot reorder by `created_at`.
- AI dependencies:
  - inference may interpret chronology but cannot redefine raw chronology.
- Lifecycle dependencies:
  - temporal and replay lifecycles.

## Invariant: Bounded AI Authority
- Why it exists: keeps trust anchored in deterministic evidence.
- What breaks if violated:
  - AI-generated truth leaks into canonical memory,
  - confidence/provenance become cosmetic,
  - hidden reasoning risk increases.
- Phase dependencies:
  - control points in `07-reasoning`, `08-retrieval`, `09-synthesis`.
- Schema dependencies:
  - confidence and inference fields.
- Replay dependencies:
  - inference replay comparability by `inference_version`.
- AI dependencies:
  - deterministic-only zones in `01-06`.
- Lifecycle dependencies:
  - inference and synthesis lifecycles.

## Invariant: Replayability
- Why it exists: evolving schemas, mappings, and inference policies require safe regeneration.
- What breaks if violated:
  - architecture cannot evolve safely,
  - bug correction requires manual patching,
  - model upgrades lose comparability.
- Phase dependencies:
  - all persisted transformation stages.
- Schema dependencies:
  - replay/version fields and mutability constraints.
- Replay dependencies:
  - isolation, version pinning, divergence reporting.
- AI dependencies:
  - inference regeneration must remain auditable.
- Lifecycle dependencies:
  - replay and supersession publication lifecycle.
