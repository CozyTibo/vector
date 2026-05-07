# Ingestion Persistence Architecture

## Persistence Scope
Phase 01 persists source-ingestion truth before canonicalization. Persistence is divided into immutable evidence stores and mutable operational state stores.

## Logical Storage Layers
- Immutable evidence layer:
  - `raw_event_envelopes`
- Operational control/state layer:
  - `ingestion_runs`
  - `ingestion_checkpoints`
  - `connector_runtime_state`
  - `queue_jobs`
  - `replay_jobs`

## Ownership Boundaries
- Phase 01 exclusively writes these tables.
- Downstream phases may read `raw_event_envelopes` (or receive events), but do not mutate ingestion control state.
- Admin/replay operations may write replay and run control tables through governed APIs only.

## Write Paths
1. Scheduler creates `queue_jobs` and `ingestion_runs`.
2. Connector worker fetches source page and normalizes envelope.
3. Persistence worker writes `raw_event_envelopes` (idempotent).
4. Checkpoint writer updates `ingestion_checkpoints`.
5. Run finalizer updates `ingestion_runs` status + metrics.

## Read Paths
- Workers read latest checkpoint and connector runtime state before polling.
- Dedupe checks read idempotency index in `raw_event_envelopes`.
- Replay workers read `replay_jobs` and replay checkpoints.
- Operators read run/checkpoint/job tables for diagnostics.

## Persistence Sequencing
- Sequence: raw write ack -> checkpoint update -> run progress update.
- Checkpoint must never advance before durable raw write.
- Run completion must never be marked before final checkpoint commit.

## Transaction Sequencing
- Tx-A: raw event persistence + dedupe conflict handling.
- Tx-B: checkpoint update (dependent on Tx-A success).
- Tx-C: ingestion run status update and metrics snapshot.
- Retry-safe because each Tx is idempotent with deterministic keys.

## Replay Interaction
- Replay writes into same raw envelope table with replay metadata tags.
- Replay checkpoints are namespace-isolated by `replay_job_id`.
- Replay cannot mutate original raw payload rows.

## Queue Interaction
- Queue jobs persist orchestration intent and retry state.
- Queue job completion state must mirror ingestion run terminal state consistency.

## Synchronous vs Asynchronous Persistence
- Synchronous: raw write + dedupe result.
- Asynchronous: downstream enqueue, aggregated run metrics rollup, some observability materializations.
