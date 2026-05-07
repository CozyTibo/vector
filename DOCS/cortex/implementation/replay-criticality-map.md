# Replay Criticality Map

## Purpose
Classify replay-critical surfaces and identify assumptions that can break replayability.

## Replay-Critical Systems (Highest Criticality)
- `02-raw-store`: immutable baseline and replay index.
- `03-canonical`: normalized truth regeneration.
- `04-entity-resolution`: identity decisions with confidence and supersession.
- `05-graph`: temporal relation evolution.
- `07-reasoning`: inference regeneration and comparability.

## Replay-Sensitive Contracts
- Identity and chronology anchors:
  - `tenant_id`, canonical ids, `source_event_id`, `occurred_at`.
- Replay/version controls:
  - `replay_job_id`, `replay_version`, `schema_version`, `extraction_version`, `processor_version`, `inference_version`.
- Lineage controls:
  - `provenance.chain_id`, `provenance.input_refs`, `provenance.source_refs`.

## Replay-Sensitive Schemas
- `schemas/contracts.md`
- `schemas/field-semantics.md`
- `schemas/temporal-modeling.md`
- `schemas/provenance-confidence.md`

## Replay-Sensitive Lifecycle Stages
- canonicalization and entity resolution corrections
- graph recomputation after relation/type policy changes
- memory projection rebuilds
- inference reruns under new `inference_version`

## Replay-Safe Mutations
- adding superseding records
- updating derived confidence through versioned re-inference
- appending replay audit metadata

## Replay-Dangerous Assumptions
- in-place mutation of historical truth records
- missing provenance in superseding outputs
- chronology recomputation from `created_at`
- unpinned inference model updates
- connector-side semantic logic changes without versioned replay path

## What Breaks Replayability
- missing raw immutability guarantees
- schema changes without replay strategy
- loss of canonical id stability rules
- inability to compare old/new outputs by replay job and version context
