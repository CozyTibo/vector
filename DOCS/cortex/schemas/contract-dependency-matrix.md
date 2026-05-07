# Contract Dependency Matrix

## Purpose
This matrix defines producer/consumer ownership, mutability, replay sensitivity, and temporal/provenance obligations for core contracts.

## CanonicalEvent
- Producers:
  - `03-canonical` (primary)
  - replay republisher for superseding variants
- Consumers:
  - `04-entity-resolution`, `05-graph`, `06-memory`, `07-reasoning`, `08-retrieval`, `09-synthesis`
- Mutability:
  - identity fields immutable (`tenant_id`, `canonical_event_id`, `occurred_at`, source refs)
  - derived facets supersedable
- Replay sensitivity:
  - high (`processor_version`, `extraction_version`, `replay_version`)
- Temporal assumptions:
  - chronology anchored by `occurred_at`
  - ingestion chronology by `observed_at`
- Provenance obligations:
  - full `provenance.*`
  - source evidence references preserved

## CanonicalEntity
- Producers:
  - `03-canonical` (initial)
  - `04-entity-resolution` (merge/split supersession)
- Consumers:
  - `05-graph`, `06-memory`, `07-reasoning`, `08-retrieval`, `09-synthesis`
- Mutability:
  - `canonical_entity_id` immutable
  - status/labels supersedable
- Replay sensitivity:
  - high for identity-linking evolutions
- Temporal assumptions:
  - `effective_from`/`effective_to` required for entity validity
- Provenance obligations:
  - mapping + resolution lineage must remain explicit

## CanonicalRelation
- Producers:
  - `03-canonical` (deterministic relation candidates)
  - `05-graph` (temporal relation materialization)
  - `07-reasoning` (inferred relation hypotheses)
- Consumers:
  - `06-memory`, `07-reasoning`, `08-retrieval`, `09-synthesis`
- Mutability:
  - relation ids immutable
  - relation status/confidence supersedable
- Replay sensitivity:
  - very high due to downstream graph and reasoning dependency
- Temporal assumptions:
  - validity windows mandatory
  - supersession lineage required
- Provenance obligations:
  - deterministic relations reference event evidence
  - inferred relations require supporting evidence + confidence

## Provenance Contract
- Producers:
  - all phases at output boundary
- Consumers:
  - all downstream phases and governance/audit tooling
- Mutability:
  - additive lineage only; no destructive rewrite
- Replay sensitivity:
  - critical (breaks divergence analysis if incomplete)
- Temporal assumptions:
  - provenance timestamps must reflect generation order
- Obligations:
  - `provenance.chain_id`, `input_refs`, `source_refs`, stage, version

## Confidence Contract
- Producers:
  - `04-entity-resolution`, `07-reasoning`, `08-retrieval` (selection confidence), `09-synthesis` (presentation confidence)
- Consumers:
  - downstream reasoning/retrieval/synthesis and governance review
- Mutability:
  - confidence values supersedable with new evidence/version
- Replay sensitivity:
  - high for inference comparability
- Temporal assumptions:
  - confidence changes must be time/version attributable
- Obligations:
  - `confidence_score`, `confidence_band`, `ambiguity_reason` when unresolved

## Replay Contract
- Producers:
  - replay orchestration + each replayed stage publisher
- Consumers:
  - all stage readers, governance, audit
- Mutability:
  - replay metadata append-only by job/version
- Replay sensitivity:
  - critical by definition
- Temporal assumptions:
  - replay does not alter source event chronology semantics
- Obligations:
  - `replay_job_id`, `replay_version`, comparison metadata

## Temporal Contract
- Producers:
  - ingestion/canonical/reasoning stages for stage-specific timestamps
- Consumers:
  - graph, memory, reasoning, retrieval, synthesis
- Mutability:
  - source chronology immutable
  - processing/inference timestamps supersedable by replay runs
- Replay sensitivity:
  - critical for reconstruction and causality
- Temporal assumptions:
  - ordering precedence: `occurred_at` -> `observed_at` -> `processed_at`
- Obligations:
  - validity ranges and supersession links maintained
