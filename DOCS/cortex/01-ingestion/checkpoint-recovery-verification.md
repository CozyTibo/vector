# Checkpoint Recovery Verification

## Verification Objective
Ensure interruption recovery is resumable, monotonic, and replay-safe across all sync modes.

## Recovery Scenarios
- incremental sync interruption after partial page persistence,
- backfill interruption mid historical window,
- replay interruption mid-scope,
- pagination token expiry mid-run,
- checkpoint write failure after successful raw writes.

## Expected Guarantees
- resume from latest stable checkpoint,
- no checkpoint regression,
- no loss of previously durable raw writes,
- no duplicate durable writes after resumption.

## Verification Probes
- crash after raw persist before checkpoint:
  - expected: replay/restore from previous checkpoint + dedupe-safe re-fetch.
- crash after checkpoint before run status update:
  - expected: run reconciles from checkpoint truth.
- corrupt latest checkpoint:
  - expected: fallback to previous stable checkpoint and anomaly flag.
- replay checkpoint isolation:
  - expected: replay checkpoint mutation never touches live checkpoint namespace.

## Validation Outputs
- checkpoint integrity report,
- recovery latency and resume depth metrics,
- duplicate/loss counters after recovery.
