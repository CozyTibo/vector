# Polling Strategy

## Polling-First Baseline
Cortex starts with polling-first ingestion. Polling must support deterministic replay and future webhook convergence without contract redesign.

## Polling Orchestration
- Scheduler assigns polling slots by tenant + connector + priority lane.
- Cadence classes:
  - high-frequency connectors (chat activity): short windows.
  - medium-frequency connectors (tickets/docs): moderate windows.
  - low-frequency connectors (meeting transcripts): longer windows.
- Staggering:
  - jittered start times to prevent synchronized spikes.
  - per-tenant fairness guardrails.

## Adaptive Polling
- Increase cadence when:
  - recent delta volume high,
  - backlog increases,
  - high-value project windows active (policy-driven).
- Decrease cadence when:
  - repeated empty windows,
  - sustained rate-limit pressure.

## Concurrency
- Concurrency caps per connector type, per tenant, and global lane.
- Live lane preempts backfill lane.
- Replay lane is isolated with explicit quota.

## Pagination + Delta Detection
- Page fetch loops continue until:
  - no next token,
  - page size below threshold,
  - bounded window exhausted.
- Delta detection uses:
  - source updated timestamp,
  - source cursor token,
  - overlap window for late updates.

## Checkpointing
- Cursor checkpoint committed only after page persistence ack.
- Checkpoint contains:
  - source cursor,
  - high watermark timestamp,
  - last page token,
  - extraction version.

## Polling -> Hybrid Webhook Evolution
- Webhooks map into same ingestion envelope contract.
- Polling remains reconciliation authority for missed webhook windows.
- Webhook mode adds trigger path; does not replace cursor/checkpoint model.
