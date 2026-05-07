# Ingestion Indexing Strategy

## Index Principles
- prioritize hot operational lookups and replay scans.
- keep write amplification acceptable for append-heavy workloads.
- avoid broad JSONB indexing unless query-driven evidence exists.

## Required Indexes
### `raw_event_envelopes`
- PK: `raw_event_id`
- unique: `ingestion_idempotency_key`
- composite:
  - (`tenant_id`, `connector_instance_id`, `source_occurred_at`)
  - (`tenant_id`, `source_object_id`)
  - (`ingestion_run_id`)
  - (`replay_job_id`, `source_occurred_at`)
  - (`tenant_id`, `source_event_id`) where source_event_id is not null

### `ingestion_runs`
- PK: `ingestion_run_id`
- composite:
  - (`tenant_id`, `connector_instance_id`, `status`, `started_at`)
  - (`replay_job_id`) where replay_job_id is not null

### `ingestion_checkpoints`
- PK: `checkpoint_id`
- unique:
  - (`tenant_id`, `connector_instance_id`, `sync_mode`, `scope_key`, `checkpoint_seq`, `replay_job_id`)
- composite:
  - (`tenant_id`, `connector_instance_id`, `sync_mode`, `scope_key`, `checkpoint_seq` desc)

### `connector_runtime_state`
- unique: (`tenant_id`, `connector_instance_id`)
- composite:
  - (`state`, `updated_at`)

### `queue_jobs`
- PK: `job_id`
- composite:
  - (`lane`, `status`, `priority`, `created_at`)
  - (`visibility_timeout_at`) for re-lease scanning
  - (`tenant_id`, `connector_instance_id`, `status`)

### `replay_jobs`
- PK: `replay_job_id`
- composite:
  - (`tenant_id`, `status`, `created_at`)
  - (`replay_version`)

## Hot Indexes
- dedupe unique index on `ingestion_idempotency_key`
- queue lane status indexes
- latest checkpoint lookup index
- replay progress scan by `replay_job_id`

## Tradeoffs
- extra indexes on raw table increase write latency; add only query-critical indexes.
- verify index utility with observability-driven access patterns.
