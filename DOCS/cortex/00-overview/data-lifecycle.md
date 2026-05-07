# System-Wide Data Lifecycle

## Lifecycle Principle
Cortex preserves lineage across all stages. Records evolve through supersession, never semantic overwrite.

## 1) Source Event Lifecycle
1. Connector fetches source payload.
2. Ingestion validates envelope and emits raw persistence request.
3. Raw store writes immutable event with source references and observation metadata.

## 2) Canonicalization Lifecycle
1. Canonical layer consumes raw events.
2. Deterministic mapping emits canonical events/entities/relations.
3. Canonical records persist with schema, extraction, and processor versions.

## 3) Identity And Graph Lifecycle
1. Entity resolution links canonical identities and emits confidence-scored links.
2. Graph layer materializes temporal relations and state transitions.
3. Conflicts remain explicit until resolved or superseded.

## 4) Inference Lifecycle
1. Reasoning consumes memory + graph evidence.
2. Inference artifacts are emitted with `confidence_score`, `confidence_band`, and `supporting_evidence_refs`.
3. Low-confidence outputs remain unresolved ambiguity artifacts.

## 5) Retrieval And Synthesis Lifecycle
1. Retrieval composes bounded context packs with provenance completeness.
2. Synthesis produces non-authoritative narratives with explicit uncertainty and evidence citations.
3. Synthesis outputs never mutate canonical or memory truth layers.

## 6) Replay Lifecycle
1. Replay trigger is declared with scope and version context.
2. Replay executes in isolation and publishes superseding outputs.
3. Replay lineage records compare previous and regenerated outputs.

## 7) Archival And Retention Lifecycle
1. Retention policies classify data by layer and sensitivity.
2. Archival preserves replay requirements and auditability.
3. Deletion requests follow tenant policy while preserving allowed audit records.

## 8) Deletion And Supersession Lifecycle
- Deletion semantics are explicit policy actions, not implicit data disappearance.
- Supersession links old and new records with validity windows.
- Historical reconstruction remains possible after supersession.

## 9) Temporal Lifecycle
- Every stage preserves event-time, observation-time, and stage processing/inference times.
- Historical state reconstruction evaluates effective validity ranges, not latest row snapshots.
