# Ingestion Storage Model

## Raw Event Envelope (Pre-Canonical)
Required envelope fields:
- `tenant_id`
- `connector_type`
- `connector_instance_id`
- `sync_run_id`
- `sync_mode`
- `source_event_id` (nullable if source lacks explicit id)
- `source_object_id`
- `source_object_type`
- `source_revision` (nullable)
- `occurred_at`
- `observed_at`
- `processed_at`
- `created_at`
- `payload_raw_jsonb`
- `payload_fingerprint`
- `ingestion_idempotency_key`
- `schema_version`
- `extraction_version`
- `processor_version`
- `replay_job_id` (nullable)
- `replay_version` (nullable)
- `provenance.chain_id`
- `provenance.source_refs`

## Storage Boundaries
- Raw payload stored immutably in primary Postgres JSONB column.
- No canonical fields persisted in raw table beyond deterministic source metadata.

## Indexing Strategy
- Unique index: `ingestion_idempotency_key`.
- Query indexes:
  - tenant + connector + occurred_at,
  - tenant + source_object_id,
  - replay_job_id,
  - sync_run_id.

## Partitioning Assumptions
- Initial: partition by time window (`created_at`) and tenant-aware indexes.
- Evolve if required by volume; keep query paths replay-focused.

## Large Payload Handling
- Store payload metadata + compressed payload strategy when payload size thresholds exceeded.
- Future S3 archival may offload large payload blobs but must preserve replay accessibility contract.

## Retention + Replay Requirements
- Raw events retained according to replay and governance policy.
- Retention changes must preserve replay feasibility for required horizons.
