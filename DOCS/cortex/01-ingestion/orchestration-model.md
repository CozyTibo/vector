# Orchestration Model

## Orchestration Primitives
- Scheduler: emits sync jobs into queue lanes.
- Queues:
  - `live_sync_queue`
  - `backfill_queue`
  - `replay_queue`
  - `recovery_queue`
  - `retry_queue`
  - `dead_letter_queue`
- Workers:
  - connector workers (fetch + normalize),
  - persistence workers (raw write + checkpoint),
  - replay workers (version-pinned runs).

## Synchronous vs Asynchronous
- Synchronous:
  - single page fetch -> normalize -> persist ack loop per worker task.
- Asynchronous:
  - scheduler dispatch,
  - retry dispatch,
  - downstream canonical enqueue.

## Ordering Guarantees
- Guaranteed:
  - per-worker task ordering.
  - per connector stream best-effort ordered checkpoint progression.
- Not guaranteed:
  - cross-connector global ordering.
  - strict ordering across independent workers for same timestamp ties.

## Isolation
- Tenant isolation: queue keys include tenant.
- Connector isolation: connector failures do not block other connector queues.
- Replay isolation: replay queue quota separate from live.

## Prioritization
- Priority order:
  1. live incremental sync,
  2. recovery sync,
  3. targeted object sync,
  4. backfill,
  5. replay (unless emergency replay mode enabled).

## Dead-Letter Handling
- Non-retryable or retry-exhausted tasks move to dead-letter queue.
- Dead-letter payload includes:
  - failure class,
  - connector + tenant context,
  - last checkpoint,
  - replay impact hint.
