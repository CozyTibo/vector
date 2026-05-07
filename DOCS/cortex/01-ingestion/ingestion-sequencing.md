# Ingestion Sequencing

## Sequencing Priorities
1. Live incremental sync.
2. Recovery sync.
3. Targeted object sync.
4. Backfill.
5. Replay (default), unless replay emergency priority is explicitly enabled.

## Per-Run Sequencing
- Sequence unit: connector stream page.
- Processing sequence:
  1. fetch page,
  2. normalize page envelopes,
  3. persist page events,
  4. commit checkpoint,
  5. fetch next page.

## Cross-Run Sequencing
- No strict ordering across connector types.
- Per tenant fairness prevents starvation by high-volume connectors.

## Replay Sequencing
- Replay uses deterministic pagination traversal recorded in replay checkpoints.
- Replay lanes cannot preempt live lanes unless operator explicitly escalates replay priority.
