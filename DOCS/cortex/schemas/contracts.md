# Core Data Contracts

## CanonicalEvent Contract
Required fields:
- `tenant_id`
- `canonical_event_id` (stable)
- `canonical_event_type`
- `occurred_at` (source event-time)
- `observed_at` (connector observation-time)
- `processed_at` (pipeline processing-time)
- `created_at` (record creation time)
- `source_refs[]` (raw event ids)
- `entity_refs[]` (canonical entity ids)
- `relation_refs[]` (optional)
- `schema_version`
- `extraction_version`
- `replay_version`
- `processor_version`

Immutable fields:
- `tenant_id`, `canonical_event_id`, `source_refs`, `occurred_at`

Replay-sensitive fields:
- `processor_version`, `extraction_version`, `replay_version`, derived enrichments, normalized facets

## CanonicalEntity Contract
Required fields:
- `tenant_id`
- `canonical_entity_id`
- `entity_type` (actor, team, artifact, project, topic, decision, etc.)
- `primary_label`
- `status` (active, merged, deprecated)
- `effective_from`, `effective_to` (nullable)
- `source_identity_refs[]`
- `schema_version`
- `created_at`
- `replay_version`

Immutable fields:
- `tenant_id`, `canonical_entity_id`, first `effective_from`

## CanonicalRelation Contract
Required fields:
- `tenant_id`
- `canonical_relation_id`
- `relation_type` (owns, blocks, depends_on, discussed_in, supersedes, etc.)
- `from_entity_id`
- `to_entity_id`
- `evidence_event_refs[]`
- `effective_from`, `effective_to` (nullable)
- `confidence_score` + `confidence_band` (required for inferred relations)
- `schema_version`
- `created_at`
- `replay_version`

## Provenance Contract
Every non-raw artifact must include:
- `provenance.chain_id`
- `provenance.input_refs[]`
- `provenance.source_refs[]`
- `provenance.transform_stage`
- `provenance.processor_version`
- `provenance.generated_at`

## Inference + Confidence Contract
Inference records require:
- `inference_type`
- `confidence_score` (0.0-1.0)
- `confidence_band` (`low|medium|high`)
- `ambiguity_reason` (nullable)
- `supporting_evidence_refs[]`
- `inferred_at`
- `inference_version` (when AI-assisted)
- `replay_version`

## Ingestion Persistence Alignment (Phase 01)

### Raw Event Persistence Contract
Required raw persistence fields:
- `raw_event_id`
- `tenant_id`
- `connector_type`
- `connector_instance_id`
- `ingestion_run_id`
- `source_event_id` (nullable if provider lacks explicit id)
- `source_object_id`
- `source_object_type`
- `source_occurred_at` (maps to source chronology anchor)
- `source_payload`
- `payload_hash`
- `ingestion_idempotency_key`
- `schema_version`
- `extraction_version`
- `processor_version`
- `replay_job_id` (nullable)
- `replay_version` (nullable)
- `provenance.chain_id`
- `provenance.source_refs[]`
- `observed_at`
- `processed_at`
- `created_at`

Immutability requirements:
- raw payload and source identity fields are append-only.
- replay and retry operations never update raw payload rows in place.

Replay-sensitive requirements:
- version fields must remain pinned and queryable.
- source chronology fields must remain stable across replay.

Contract stability requirements:
- frozen-core semantics are governed by `../01-ingestion/raw-envelope-contract-stability.md`.
- replay critical classification is governed by `../01-ingestion/replay-critical-fields.md`.
- schema evolution must follow `../01-ingestion/schema-evolution-rules.md`.

### Ingestion Run Contract
Required fields:
- `ingestion_run_id`
- `tenant_id`
- `connector_instance_id`
- `sync_mode`
- `status`
- `started_at`
- `completed_at` (required for terminal statuses)
- `retry_count`
- `failure_reason_code` (nullable)
- `replay_job_id` (nullable)
- `replay_version` (nullable)

State and transition requirements:
- status transitions must follow ingestion state-machine constraints.
- terminal state mutation is limited to operator annotations, not status rollback.

### Checkpoint Contract
Required fields:
- `checkpoint_id`
- `tenant_id`
- `connector_instance_id`
- `sync_mode`
- `scope_key`
- `checkpoint_seq` (monotonic per scope)
- `cursor_token` (nullable by source model)
- `pagination_token` (nullable)
- `high_watermark_at`
- `updated_at`
- `replay_job_id` (nullable, required for replay namespace)

Mutation requirements:
- checkpoint progression is monotonic and non-regressive.
- replay checkpoints are isolated from live checkpoint namespace.

### Idempotency Contract
Required fields:
- `source_identity_key`
- `payload_hash`
- `ingestion_idempotency_key` (unique)

Guarantees:
- retries and overlap windows are safe under at-least-once orchestration.
- duplicate raw persistence is prevented by deterministic uniqueness constraints.

### Transaction Boundary Contract
Atomic unit requirements:
1. raw persistence + dedupe registration
2. checkpoint update after raw persistence success
3. run progress/status update after checkpoint success

Failure handling requirements:
- partial failures preserve durable successful raw writes.
- retries must be idempotent and replay-safe.
