# Replay Consistency Verification

## Verification Scope
Validate replay determinism, completeness, ordering, provenance continuity, and checkpoint behavior.

## Determinism Checks
- fixed scope + fixed version tuple -> stable envelope identity set.
- explainable divergence only when version tuple changes.

## Completeness Checks
- replay expected source identity count equals persisted replay scope count (minus explicitly quarantined items).
- no unaccounted scope gaps.

## Equivalence Checks
- compare:
  - idempotency identity set,
  - key timestamp distributions,
  - payload hash distributions,
  - provenance completeness rates.

## Ordering Stability Checks
- replay traversal produces stable sequence markers per scope.
- no checkpoint sequence regression.

## Provenance Continuity Checks
- every replay-produced row has required provenance bootstrap fields.
- provenance chain continuity preserved across replay runs.

## Checkpoint Behavior Checks
- replay checkpoint namespace isolation.
- resumable progress from highest stable checkpoint.

## Trust Decision
Replay is acceptable for organizational memory reconstruction only when:
- no critical invariant breaches,
- no unexplained divergence,
- completeness and provenance checks pass.
