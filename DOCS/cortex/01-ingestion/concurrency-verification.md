# Concurrency Verification

## Objective
Verify lock, lease, and overlap controls prevent duplicate persistence and checkpoint corruption.

## Verification Areas
- concurrent polling on same connector scope,
- concurrent replay runs with overlapping scopes,
- retry overlap with active live run,
- cross-tenant concurrent high-load runs,
- checkpoint writer contention.

## Required Verifications
- lock correctness:
  - only one active checkpoint writer per scope namespace.
- lease correctness:
  - queue visibility timeout re-leases do not create duplicate commits.
- overlap prevention:
  - conflicting replay scopes rejected or serialized.
- isolation correctness:
  - one scope's contention does not block unrelated connectors/tenants.

## Corruption Signals
- duplicate idempotency keys committed,
- checkpoint_seq regressions,
- run status oscillation outside allowed transitions,
- replay/live pointer collision.
