# Ingestion Run Schema

## Table: `ingestion_runs`
Purpose: operational record for each sync execution.

## Primary Key
- `ingestion_run_id` (immutable).

## Core Fields
- `tenant_id`
- `connector_instance_id`
- `sync_mode` (`incremental`, `backfill`, `replay`, `recovery`, `targeted`)
- `replay_mode` (boolean)
- `start_cursor`, `end_cursor`
- `status` (`REGISTERED`, `SCHEDULED`, `RUNNING`, `CHECKPOINTING`, `PARTIAL_FAILURE`, `RETRYING`, `FAILED`, `COMPLETED`)
- `started_at`, `completed_at`
- `retry_count`
- `failure_reason_code`, `failure_reason_detail`
- `throttling_state`, `throttle_events`
- throughput metrics (`events_processed`, `pages_processed`, `bytes_processed`, `avg_latency_ms`, `p95_latency_ms`)
- replay context (`replay_job_id`, `replay_version`, nullable)

## Lifecycle Rules
- status transitions follow ingestion state machine.
- terminal statuses are immutable except operator-governed remediation annotation fields.
- `completed_at` required for terminal states.

## Checkpoint Ownership
- run owns mutable checkpoint progression pointer but checkpoint rows persist separately.
- run end_cursor must match last successful checkpoint when completed.

## Replay Implications
- replay runs must include replay context.
- replay and live runs cannot share cursor namespace.

## Observability Obligations
- run must persist sufficient metrics for SLO evaluation and failure triage.
