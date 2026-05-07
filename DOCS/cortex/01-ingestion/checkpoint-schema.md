# Checkpoint Schema

## Table: `ingestion_checkpoints`
Purpose: durable sync progress snapshots for resumable ingestion.

## Primary Key
- `checkpoint_id`

## Checkpoint Scope Keys
- `tenant_id`
- `connector_instance_id`
- `sync_mode`
- `scope_key` (stream/object/window identity)
- optional `replay_job_id`

## Checkpoint Fields
- `cursor_token`
- `pagination_token`
- `window_start`, `window_end`
- `high_watermark_at`
- `last_processed_source_identity`
- `processed_count`
- `failed_count`
- `checkpoint_seq` (monotonic per scope)
- `status` (`ACTIVE`, `STALE`, `FINALIZED`)
- `updated_at`

## Mutation Rules
- checkpoints are append-preferred with monotonic `checkpoint_seq`.
- current pointer may be materialized in run/connector state for faster lookup.
- no checkpoint regression: lower sequence cannot replace higher sequence.

## Replay-Safe Semantics
- replay checkpoints are namespace-isolated by `replay_job_id`.
- live checkpoints must not be mutated by replay unless explicit replacement workflow is approved.

## Recovery Semantics
- run recovery starts from highest valid checkpoint_seq.
- if checkpoint invalid/corrupt, recovery uses nearest previous stable checkpoint and emits anomaly.

## Partial Progress Guarantees
- successfully persisted pages are never re-lost.
- overlap re-fetch is acceptable; dedupe layer prevents duplicate row creation.
