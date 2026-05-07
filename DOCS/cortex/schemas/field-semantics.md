# Canonical Field Semantics

## Naming Convention
- `snake_case` for all fields.
- `*_id` for identifiers.
- `*_at` for timestamps (UTC).
- `*_version` for versioned processors/models/schemas.
- `effective_*` for temporal validity windows.
- Arrays end with `_refs` for references.

## Identifier Fields
- `tenant_id`: immutable tenant scope key. Required in every persisted record.
- `canonical_event_id`: immutable id for canonical event identity.
- `canonical_entity_id`: immutable id for canonical entity identity.
- `canonical_relation_id`: immutable id for canonical relation identity.
- `canonical_id`: generic alias used only in abstract docs; implementation contracts must use typed ids above.
- `source_event_id`: source-native event id when available; immutable if present.
- `replay_job_id`: replay execution identity for audit and lineage.

## Timestamp Fields
- `occurred_at`: event-time in source system (when reality happened).
- `observed_at`: connector observation-time (when source was fetched/seen).
- `processed_at`: transformation-time for deterministic stages.
- `inferred_at`: generation-time for inference artifacts.
- `created_at`: persistence creation time in current storage layer.
- `effective_from`: start of validity range for entities/relations/states.
- `effective_to`: end of validity range (`null` means currently effective).

## Provenance Fields
- `provenance.chain_id`: lineage chain identity across stages.
- `provenance.input_refs`: immediate upstream artifact references.
- `provenance.source_refs`: raw source evidence references.
- `derived_from`: optional convenience pointer; if used, it must duplicate a value present in `provenance.input_refs`.
- `provenance.transform_stage`: stage label (`ingestion|canonical|...`).
- `provenance.processor_version`: deterministic logic version.
- `provenance.generated_at`: provenance metadata generation timestamp.

## Confidence And Ambiguity Fields
- `confidence_score`: numeric confidence in `[0.0, 1.0]`.
- `confidence_band`: categorical confidence (`low|medium|high`).
- `ambiguity_reason`: explicit unresolved ambiguity rationale.
- `supporting_evidence_refs`: references to evidence used for inference.
- `conflict_status`: `open|resolved|superseded` for contradictory assertions.

## Version Fields
- `schema_version`: contract schema version for record shape.
- `extraction_version`: deterministic extraction ruleset version.
- `inference_version`: inference policy/model bundle version.
- `replay_version`: replay policy/version context used for regenerated outputs.
- `processor_version`: deterministic processor version for stage transformation.

## Mutability Rules
- Immutable: ids, tenant scope, source references, `occurred_at`.
- Supersedable: normalized labels, inferred links, confidence fields.
- Never mutate in place where lineage matters; emit superseding records.

## Replay Sensitivity
- Fields that can change under replay with new logic: derived attributes, inferred links, confidence values.
- Fields that must not change under replay: immutable ids, tenant scope, source evidence references.

## Ownership
- Ingestion owns `observed_at`, envelope identity.
- Canonical owns canonical ids and normalized type fields.
- Entity resolution owns identity-link confidence fields.
- Reasoning owns `inferred_at`, inference-specific confidence metadata.
- Admin/replay owns replay metadata fields (`replay_job_id`, `replay_version`).
