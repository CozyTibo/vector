# Ingestion Observability

## Health Definition
Ingestion is healthy when:
- sync lag remains within policy SLO,
- retry and dead-letter rates stay below thresholds,
- checkpoint progression is monotonic,
- replay backlog is bounded and isolated from live SLO impact.

## Required Metrics
- per connector + tenant:
  - sync lag,
  - events ingested/sec,
  - p50/p95 ingestion latency,
  - retry rate,
  - dead-letter count,
  - throttle duration,
  - auth failure count.
- replay metrics:
  - replay progress %,
  - replay throughput,
  - replay divergence counters.
- queue metrics:
  - lane backlog,
  - worker utilization,
  - queue age.

## Required Logs
- structured log keys:
  - tenant_id, connector_type, sync_run_id, sync_mode, checkpoint_id, failure_class, replay_job_id.

## Alerts
- sustained lag breach,
- dead-letter growth,
- repeated auth failures,
- replay stalled state,
- retry storm detection.

## Operator Dashboards
- connector fleet health,
- tenant ingestion health,
- replay operations panel,
- queue pressure and saturation.
