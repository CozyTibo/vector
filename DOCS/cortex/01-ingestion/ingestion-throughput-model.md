# Ingestion Throughput Model

## Planning Assumptions
- Multi-tenant ingestion with uneven connector distribution.
- Burst-heavy chat connectors and slower doc/ticket connectors.
- Replay and backfill can temporarily exceed live throughput demands.

## Throughput Dimensions
- Events/sec per connector.
- Envelope normalization latency.
- Raw persistence write throughput.
- Queue backlog growth rate.
- Checkpoint commit latency.

## Capacity Envelopes (Design-Level Targets)
- Live ingestion:
  - maintain bounded lag under normal burst windows.
- Backfill:
  - progress without violating live SLO.
- Replay:
  - isolated throughput budget with predictable completion estimates.

## Scaling Controls
- Horizontal worker scaling by queue lane.
- Concurrency caps per connector and tenant.
- Adaptive cadence reductions during saturation.
- Backpressure when raw persistence latency spikes.

## Large Transcript Handling
- Meeting transcript payloads require higher payload-size budget and potentially lower concurrency lanes.
- Large payload ingestion must preserve idempotency and replay metadata equivalence.
