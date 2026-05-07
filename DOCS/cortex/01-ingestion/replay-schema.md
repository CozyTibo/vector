# Replay Schema

## Table: `replay_jobs`
Purpose: persistent definition and lifecycle of replay operations.

## Core Fields
- `replay_job_id`
- `replay_version`
- `tenant_id`
- `status` (`REGISTERED`, `RUNNING`, `CHECKPOINTING`, `FAILED`, `COMPLETED`, `CANCELLED`)
- scope fields:
  - `connector_scope`
  - `time_window_start`, `time_window_end`
  - `object_scope` (nullable)
- version pinning:
  - `schema_version`
  - `extraction_version`
  - `processor_version`
  - optional `inference_version` reference for downstream correlation
- boundaries:
  - `created_at`, `started_at`, `completed_at`
  - `requested_by`
  - `priority`
- metrics:
  - `events_replayed`
  - `divergence_count`
  - `failure_count`

## Supporting Table: `replay_dependencies` (logical)
- maps replay jobs to affected connectors, runs, checkpoints, and downstream dependency notes.

## Replay Checkpoint Linkage
- replay checkpoints stored in `ingestion_checkpoints` with `replay_job_id`.
- replay progress computed from checkpoints + job scope.

## Isolation Semantics
- replay job cannot mutate live checkpoint pointers unless approved replacement mode.
- replay job publication strategy is append/supersede, not in-place mutation.

## Determinism Requirements
- job must preserve version pinning and scope determinism.
- repeated replay with same version + scope should be output-comparable.
