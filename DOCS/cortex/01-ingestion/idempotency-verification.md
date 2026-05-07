# Idempotency Verification

## Verification Objectives
Prove that ingestion remains duplicate-safe under retries, overlap windows, replay, and concurrency.

## Probe Classes
- Duplicate delivery probe:
  - inject identical source payload multiple times.
  - expected: single durable raw row for idempotency key.
- Retry duplication probe:
  - simulate persistence timeout after commit, then retry.
  - expected: retry no-op on raw insert; checkpoint logic safe.
- Replay duplication probe:
  - replay same scope twice with identical versions.
  - expected: no duplicate raw rows; equivalence report stable.
- Polling overlap probe:
  - enforce overlapping window fetches.
  - expected: no duplicate durable persistence.
- Concurrency duplicate probe:
  - run competing workers on same scope.
  - expected: uniqueness constraint and lock semantics prevent duplication.

## Identity Determinism Validation
- validate `source_identity_key` derivation stability.
- validate `payload_hash` stability for canonicalized payload bytes.
- validate `ingestion_idempotency_key` deterministic composition across workers.

## Corruption Definitions
- duplicate corruption:
  - multiple committed rows for same idempotency key.
- false dedupe:
  - distinct source revisions collapsed incorrectly to one row.
- replay duplication leakage:
  - replay produces duplicates that bypass dedupe due to key drift.
