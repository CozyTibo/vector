# Architectural Traceability Matrix

## Purpose
This matrix makes Cortex architecture enforceable by mapping each non-negotiable rule to the documents, contracts, phases, and governance checks that uphold it.

## Traceability Entries

### Invariant: Raw events are immutable
- Why it exists: replay, auditability, and provenance require source-faithful anchors.
- Enforcing documents:
  - `00-overview/architectural-invariants.md`
  - `schemas/contracts.md`
  - `implementation/replay-architecture.md`
  - `implementation/replay-integrity-audit.md`
- Related contracts:
  - `source_event_id`
  - `provenance.source_refs`
  - immutable `occurred_at`
- Related phases:
  - `01-ingestion`
  - `02-raw-store`
  - downstream consumers `03-09`
- Related schemas:
  - `schemas/contracts.md`
  - `schemas/field-semantics.md`
- Replay dependencies:
  - full replay from raw baseline
  - targeted replay integrity by source references
- AI boundary dependencies:
  - AI cannot create or mutate raw facts
- Temporal dependencies:
  - source chronology anchored by `occurred_at` and `observed_at`
- Governance checks:
  - `00-overview/drift-detection-checklist.md` (Contract, Replay, Temporal)

### Invariant: Provenance must remain reconstructable
- Why it exists: explainability and trust depend on continuous evidence lineage.
- Enforcing documents:
  - `schemas/provenance-confidence.md`
  - `schemas/field-semantics.md`
  - `00-overview/data-lifecycle.md`
- Related contracts:
  - `provenance.chain_id`
  - `provenance.input_refs`
  - `provenance.source_refs`
  - `supporting_evidence_refs`
- Related phases:
  - all phases `01-10` (handoff continuity)
- Related schemas:
  - `schemas/contracts.md`
  - `schemas/provenance-confidence.md`
- Replay dependencies:
  - replay publication requires provenance continuity across superseding records
- AI boundary dependencies:
  - inferred artifacts must include provenance + confidence
- Temporal dependencies:
  - lineage must preserve supersession sequence over time
- Governance checks:
  - `drift-detection-checklist.md` (Provenance, Replay)

### Invariant: Deterministic-first architecture
- Why it exists: predictability and reproducibility are prerequisites for cognition infrastructure.
- Enforcing documents:
  - `00-overview/principles.md`
  - `00-overview/ai-philosophy.md`
  - `implementation/extraction-strategy.md`
- Related contracts:
  - `extraction_version`
  - `processor_version`
  - deterministic timestamp semantics
- Related phases:
  - deterministic baseline in `01-06`, bounded inference in `07-09`
- Related schemas:
  - `schemas/field-semantics.md`
  - `schemas/contracts.md`
- Replay dependencies:
  - deterministic outputs stable for identical inputs/versions
- AI boundary dependencies:
  - AI invoked only after deterministic extraction and ambiguity marking
- Temporal dependencies:
  - deterministic chronology uses `occurred_at` precedence
- Governance checks:
  - `drift-detection-checklist.md` (Confidence/AI, Contract, Replay)

### Invariant: Connectors are adapters only
- Why it exists: prevents tool-specific intelligence leakage and hidden coupling.
- Enforcing documents:
  - `00-overview/connector-philosophy.md`
  - `00-overview/architectural-invariants.md`
  - phase docs in `01-ingestion/`
- Related contracts:
  - ingestion envelope and source references
- Related phases:
  - `01-ingestion` only for fetch/validate/handoff
- Related schemas:
  - `schemas/event-envelope.md`
  - `schemas/field-semantics.md`
- Replay dependencies:
  - replay depends on source-faithful connector output, not connector inference
- AI boundary dependencies:
  - AI forbidden in connector and ingestion extraction core
- Temporal dependencies:
  - connector must preserve `observed_at` semantics
- Governance checks:
  - `drift-detection-checklist.md` (Phase Boundary, AI Boundary)

### Invariant: Canonical layer is tool-agnostic organizational truth layer
- Why it exists: cross-tool reasoning requires normalized semantics.
- Enforcing documents:
  - `schemas/contracts.md`
  - `schemas/organizational-ontology.md`
  - `03-canonical/*`
- Related contracts:
  - `canonical_event_id`
  - `canonical_entity_id`
  - `canonical_relation_id`
- Related phases:
  - producer: `03-canonical`
  - consumer: `04-09`
- Related schemas:
  - `schemas/organizational-ontology.md`
  - `schemas/canonical-concepts.md`
- Replay dependencies:
  - canonical regeneration from raw under versioned mappings
- AI boundary dependencies:
  - AI cannot replace canonical deterministic mapping
- Temporal dependencies:
  - `effective_from`/`effective_to` semantics on entities/relations
- Governance checks:
  - ontology and schema review triggers in `governance-escalation-model.md`

### Invariant: Temporal reconstruction must remain possible
- Why it exists: Cortex value depends on historical replay and causal reconstruction.
- Enforcing documents:
  - `schemas/temporal-modeling.md`
  - `00-overview/data-lifecycle.md`
  - `schemas/temporal-dependency-matrix.md`
- Related contracts:
  - `occurred_at`, `observed_at`, `processed_at`, `inferred_at`
  - `effective_from`, `effective_to`
  - supersession links
- Related phases:
  - graph/memory/reasoning/synthesis (`05-09`)
- Related schemas:
  - `schemas/temporal-modeling.md`
  - `schemas/field-semantics.md`
- Replay dependencies:
  - replay cannot reorder event chronology by storage creation time
- AI boundary dependencies:
  - AI cannot override temporal ordering rules
- Temporal dependencies:
  - explicit chronology precedence and validity windows
- Governance checks:
  - `drift-detection-checklist.md` (Temporal, Replay)

### Invariant: AI is bounded and non-authoritative
- Why it exists: prevents epistemic drift into opaque AI-owned truth.
- Enforcing documents:
  - `00-overview/ai-philosophy.md`
  - `00-overview/ai-boundary-audit.md`
  - `00-overview/ai-boundary-enforcement-map.md`
- Related contracts:
  - `confidence_score`, `confidence_band`
  - `ambiguity_reason`
  - `inference_version`
  - `supporting_evidence_refs`
- Related phases:
  - primarily `07-reasoning`, `09-synthesis`; constrained support in retrieval
- Related schemas:
  - `schemas/provenance-confidence.md`
  - `schemas/field-semantics.md`
- Replay dependencies:
  - inference replay must remain version-pinned and comparable
- AI boundary dependencies:
  - deterministic-only zones remain protected (`01-06`)
- Temporal dependencies:
  - inference timing uses `inferred_at`, not source chronology replacement
- Governance checks:
  - AI-boundary review escalation for scope expansions

### Invariant: Replay is mandatory and safe
- Why it exists: evolving cognition systems require reprocessing with integrity.
- Enforcing documents:
  - `implementation/replay-architecture.md`
  - `implementation/replay-integrity-audit.md`
  - `implementation/replay-criticality-map.md`
- Related contracts:
  - `replay_job_id`
  - `replay_version`
  - stage/version fields used in comparisons
- Related phases:
  - all stages `02-09` are replay consumers/producers
- Related schemas:
  - `schemas/contracts.md`
  - `schemas/field-semantics.md`
- Replay dependencies:
  - isolation from live writes
  - superseding publication strategy
- AI boundary dependencies:
  - inference replay is allowed only with explicit version pinning
- Temporal dependencies:
  - replay must preserve event-time chronology and supersession lineage
- Governance checks:
  - mandatory replay review for schema/inference changes
