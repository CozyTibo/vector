# Idempotency Strategy

## Objectives
Prevent duplicate ingestion across:
- repeated polling windows,
- retries,
- replay reruns,
- partial persistence failures.

## Deterministic Identity Keys
- `source_identity_key`: tenant + connector + source object id + source event id/revision.
- `payload_fingerprint`: stable hash over normalized source payload bytes.
- `ingestion_idempotency_key`: source identity key + extraction version + envelope schema version.

## Deduplication Layers
1. Source-level dedupe:
   - identical source event id + revision skipped.
2. Connector-level dedupe:
   - duplicate page overlap suppressed via idempotency key.
3. Persistence-level dedupe:
   - unique constraint/index on idempotency key.
4. Replay dedupe:
   - replay context aware dedupe prevents duplicate replay writes for same replay scope checkpoint.

## Retry-Safe Behavior
- Retried persistence attempts must be no-op when idempotency key already committed.
- Checkpoint updates are idempotent by run + page token.

## Conflicting Source Updates
- Same source identity with new revision:
  - persist as new immutable raw event with explicit source revision metadata.
- Never overwrite prior payload.
