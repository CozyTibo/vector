# Retry & Failure Strategy

## Failure Classification
- Transient: network timeout, temporary provider error, DB timeout.
- Throttle: explicit rate-limit responses.
- Auth: invalid/expired token, missing scopes.
- Data quality: malformed payload, schema-incompatible object.
- Persistence: partial write, conflict, checkpoint failure.
- Replay-specific: version mismatch, replay scope corruption.

## Retry Policy
- Transient:
  - exponential backoff + jitter, bounded max attempts.
- Throttle:
  - honor provider `Retry-After`, then exponential backoff.
- Auth:
  - no blind retry; transition to `AUTH_FAILED`, alert operator.
- Data quality:
  - non-retryable by default; quarantine item and continue run.
- Persistence:
  - retry write with idempotency key.
- Replay-specific:
  - retry resumable checkpoint; escalate if repeated divergence errors.

## Escalation Behavior
- Repeated failures push connector to `DEGRADED`.
- Retry budget exhausted -> dead-letter + operator alert.
- High failure ratio in live lane can trigger automatic throttle policy.

## Replay Implications
- Retries must not duplicate replay outputs.
- Failed replay runs remain resumable with pinned version context.
- Replay failures are tracked separately from live ingestion failures.

## Operator Visibility
- Required dimensions:
  - tenant, connector, sync mode, failure class, retry attempt, last checkpoint, replay context.
