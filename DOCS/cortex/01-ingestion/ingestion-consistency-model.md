# Ingestion Consistency Model

## Consistency Modes By Concern
- Strong consistency required for:
  - raw insert + dedupe uniqueness,
  - checkpoint monotonic updates,
  - queue lease ownership.
- Eventual consistency acceptable for:
  - aggregated run metrics,
  - some observability rollups,
  - dashboard materializations.

## Ordering Consistency
- per connector stream: deterministic best-effort chronology.
- cross connector streams: eventual convergence, no total order guarantee.
- replay ordering must be deterministic for fixed scope/version context.

## Checkpoint Consistency
- latest checkpoint pointer must reflect highest successful durable progress.
- checkpoint reads may be stale in replicas; writes must use primary consistency.

## Queue Consistency
- at-least-once delivery with idempotent processing guarantees.
- visibility timeout reprocessing relies on idempotency keys and checkpoint guards.

## Deterministic Reconstruction Guarantees
- for fixed source payload and fixed versions, ingestion envelope generation is deterministic.
- replay reconstruction depends on immutable raw rows + version pinning.
