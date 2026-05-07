# Replay Query Model

## Objective
Define replay access/query patterns and challenge their cost under realistic long-horizon workloads.

## Replay Query Families
- full-history replay scans,
- scope-limited replay (tenant/tool/object/time),
- selective phase replay (partial pipeline),
- replay-vs-baseline divergence inspection,
- replay completeness and gap verification.

## Replay Cost Drivers
- data volume scanned,
- replay ordering guarantees,
- downstream derivation fanout,
- index design quality for replay selectors,
- cold-data rehydration needs.

## Failure Modes
- replay queue starvation from broad replays,
- contention with live ingestion workloads,
- degraded operator diagnostics while replay is active,
- replay completion unpredictability.

## Required Guardrails
- replay scope estimation before execution,
- replay quotas and isolation lanes,
- priority policies for trust-critical replay jobs,
- replay-specific observability and SLO tracking.

## Decision Trigger
If replay workloads consistently threaten ingestion or operator workflows, introduce dedicated replay acceleration before adding other cognition layers.
