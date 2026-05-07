# Queue/Job Schema

## Table: `queue_jobs`
Purpose: persisted orchestration tasks with retry/dead-letter behavior.

## Core Fields
- `job_id`
- `job_type` (`sync`, `replay`, `retry`, `dead_letter`, `scheduled_poll`, `recovery`)
- `lane` (`live`, `backfill`, `replay`, `retry`)
- `tenant_id`
- `connector_instance_id`
- `ingestion_run_id` (nullable)
- `replay_job_id` (nullable)
- `payload_ref` / job payload blob
- `status` (`QUEUED`, `LEASED`, `RUNNING`, `ACKED`, `FAILED`, `DEAD_LETTERED`)
- `attempt_count`, `max_attempts`
- `visibility_timeout_at`
- `next_retry_at`
- `last_error_code`, `last_error_detail`
- `priority`
- `created_at`, `updated_at`

## Ownership
- scheduler owns initial job creation.
- workers own lease/ack/failure updates.
- dead-letter handler owns terminal dead-letter transitions.

## Retry Semantics
- retry job generated with incremented attempt_count and backoff delay.
- attempt_count > max_attempts transitions to dead-letter.

## Concurrency Assumptions
- leasing semantics prevent double-execution.
- visibility timeout expiry permits safe re-lease if worker crashes.

## Replay Interaction
- replay jobs are lane-isolated and include `replay_job_id`.
- replay queue pressure must not consume live lane budget.
