# Ingestion Storage Invariants

## Invariant 1: Raw Event Immutability
- Law: raw envelope rows are append-only.
- Violation impact: replay baseline corruption, non-auditable history.

## Invariant 2: Deterministic Dedupe Identity
- Law: `ingestion_idempotency_key` derivation is deterministic for same source identity + versions.
- Violation impact: duplicate rows or false dedupe skips.

## Invariant 3: Monotonic Checkpoint Progression
- Law: checkpoint sequence and cursor progression must not regress.
- Violation impact: data loss risk or repeated churn loops.

## Invariant 4: Replay Isolation
- Law: replay state/checkpoints are isolated from live state by default.
- Violation impact: live ingestion disruption, cursor corruption.

## Invariant 5: Provenance Bootstrap Continuity
- Law: every raw row includes provenance bootstrap references sufficient for downstream lineage.
- Violation impact: non-reconstructable evidence chains.

## Invariant 6: Tenant/Connector Isolation
- Law: state and queue keys are tenant+connector scoped.
- Violation impact: cross-tenant contamination and cascading failures.

## Invariant 7: Version Pinning Persistence
- Law: schema/extraction/processor/replay versions persisted with raw rows and runs.
- Violation impact: replay comparability failure.

## Invariant 8: Frozen Core Contract Stability
- Law: replay-critical frozen envelope field semantics must not change in-place across implementation/runtime revisions.
- Violation impact: replay divergence, idempotency drift, provenance discontinuity.

## Invariant Policy References
- `raw-envelope-contract-stability.md`
- `replay-critical-fields.md`
- `schema-evolution-rules.md`
