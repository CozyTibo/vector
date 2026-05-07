# Replay Verification Model

## Trust Criteria
Replay is trusted only if all criteria pass:
- deterministic behavior for fixed input + version set,
- complete scope coverage,
- ordering stability,
- checkpoint resumability,
- isolation from live cursor/runtime mutation.

## Verification Dimensions
- Deterministic replay expectation:
  - same scope + same versions -> equivalent envelope outputs.
- Equivalence validation:
  - compare counts, idempotency identities, key field hashes.
- Divergence detection:
  - detect changed outputs, classify by expected version-driven vs unexpected drift.
- Ordering validation:
  - ensure replay traversal honors defined ordering precedence.
- Isolation validation:
  - verify no live checkpoint/runtime pointers changed.
- Checkpoint validation:
  - verify replay resumes from last replay checkpoint.
- Version pinning validation:
  - confirm replay job persisted schema/extraction/processor/replay versions.
- Mutation detection:
  - verify no updates to existing raw rows.

## Replay Verdict Classes
- `TRUSTED`: expected divergences only; invariants preserved.
- `CONDITIONALLY_TRUSTED`: minor non-critical anomalies; bounded blast radius.
- `UNTRUSTED`: unexplained divergence or invariant breach.
