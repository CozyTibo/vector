# Backfill Strategy

## Objectives
Safely ingest multi-year history without:
- overwhelming provider rate limits,
- starving live ingestion,
- violating idempotency,
- losing checkpoints.

## Backfill Modes
- Tenant bootstrap backfill.
- Connector-specific historical backfill.
- Partial historical window backfill.
- Progressive backfill (oldest-first chunking).

## Large-History Handling
- Time-window chunking (e.g., month/week slices).
- Bounded page budgets per run.
- Adaptive throttling under sustained rate-limit responses.

## Checkpoint Resumption
- Backfill checkpoints persist:
  - time window bounds,
  - page token,
  - processed count,
  - retry counters.
- Resumption continues from last committed checkpoint.

## Replay Compatibility
- Backfill writes same envelope schema as live runs.
- Replay metadata optional for live bootstrap; required for replay-initiated backfill.

## Observability
- Track:
  - historical coverage progress,
  - backlog remaining,
  - per-window failure hotspots.
