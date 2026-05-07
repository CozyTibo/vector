# Storage Bottleneck Analysis

## Objective
Identify likely bottlenecks early so architecture evolution is proactive, not crisis-driven.

## Probable Bottlenecks
- full-window replay scans,
- temporal range joins with supersession checks,
- recursive provenance/lineage traversal,
- linkage fanout and ambiguity branch expansion,
- index maintenance contention on hot write paths.

## Early Warning Signs
- steady replay completion time growth,
- recurring operator query timeouts,
- ingestion latency regression despite constant input rate,
- increasing query plan volatility.

## Bottleneck Triage Order
1. isolate workload class causing contention,
2. tune query/index strategy for that class,
3. add targeted acceleration if tuning is insufficient,
4. escalate to architecture expansion only with evidence.

## Guardrail
Avoid global fixes for local bottlenecks; each query family may need different mitigation.
