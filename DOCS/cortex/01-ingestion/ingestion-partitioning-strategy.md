# Ingestion Partitioning Strategy

## Baseline Strategy
Start with single logical tables plus tenant/time composite indexes. Partition only when measured write/read pressure requires it.

## Future Partition Axes
- time partitioning (primary candidate) on `created_at` for raw events.
- optional sub-partitioning by `tenant_id` hash for very large multi-tenant scale.
- replay-local partition hints for heavy replay windows (logical isolation).

## Partition Evolution Triggers
- raw table write amplification beyond acceptable thresholds.
- replay scans impacting live ingestion latency.
- vacuum/index maintenance pressure on large unpartitioned tables.

## Replay Implications
- replay often scans time windows; time partitions reduce scan breadth.
- partition pruning must preserve deterministic chronological traversal.

## Archival Implications
- cold partitions can be archived according to retention policy.
- archival must preserve replay-required horizon and provenance accessibility.

## Indexing Implications
- partition-local indexes required for hot lookups.
- global uniqueness (e.g., idempotency keys) may require strategy for cross-partition enforcement.

## Throughput Implications
- partitioning can improve write concurrency but increases operational complexity.
- adopt only with explicit operational evidence and migration plan.
