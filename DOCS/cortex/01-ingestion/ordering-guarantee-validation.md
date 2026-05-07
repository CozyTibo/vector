# Ordering Guarantee Validation

## Ordering Classes
- Strict (required):
  - checkpoint sequence monotonicity per scope.
- Deterministic best-effort:
  - connector-stream event traversal using ordering precedence.
- Eventual:
  - cross-connector reconciliation in downstream layers.
- Undefined (explicitly relaxed):
  - global total order across all connectors and tenants.

## Validation Targets
- Source ordering:
  - verify source chronology capture (`source_occurred_at`, ordering metadata).
- Ingestion ordering:
  - verify per-scope progression and no checkpoint regression.
- Replay ordering:
  - verify replay traversal remains stable for fixed scope/version.
- Checkpoint ordering:
  - verify highest stable checkpoint reflects durable progress.
- Eventual reconciliation:
  - verify known out-of-order arrivals are recoverable via overlap windows + dedupe.

## Ordering Breach Symptoms
- repeated backward checkpoint jumps,
- missing middle pages in chronology window,
- replay output with unexplained sequence inversions.
