# Ingestion Transaction Boundaries

## Atomic Persistence Units
1. Raw event persistence + dedupe registration.
2. Checkpoint progression update.
3. Ingestion run status and metrics update.
4. Queue job state transition (lease/ack/fail/dead-letter).

## Boundary Rules
- raw event insert and dedupe key registration are atomic.
- checkpoint update is separate and occurs only after raw insert success.
- run update occurs after checkpoint update.
- queue ack occurs after run/checkpoint updates confirm durable success.

## Rollback Semantics
- if raw insert fails: no checkpoint advance, no run progress increment.
- if checkpoint update fails after raw insert:
  - raw row remains,
  - run marked partial failure,
  - retry checkpoint update idempotently.
- if run update fails:
  - retry run update without rewriting raw row.

## Partial Failure Behavior
- page-level partial failure allowed with persisted successes retained.
- retries operate from last successful checkpoint.

## Retry-Safe Guarantees
- idempotency keys prevent duplicate raw writes.
- checkpoint sequence guards prevent rollback/regression.
- run state transitions enforce monotonic progress to terminal state.

## Replay-Safe Guarantees
- replay transactions are isolated by replay scope.
- replay cannot atomically include live checkpoint mutation unless explicit controlled mode.
