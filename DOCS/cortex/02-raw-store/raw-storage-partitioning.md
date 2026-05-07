# Raw Storage Partitioning

## Baseline
Start non-partitioned with disciplined indexing, then evolve partitioning only when measured pressure justifies migration complexity.

## Preferred Evolution Order
1. time partitioning on highest-growth raw tables,
2. optional tenant-aware subdivision only if tenant skew creates hotspots,
3. archival-aligned partition lifecycle once cold volume dominates.

## Trigger Conditions
- replay scan latency breach for bounded windows,
- maintenance window overrun (vacuum/index maintenance pressure),
- persistent write contention on hot raw tables.

## Replay Safety Requirements
- partition pruning must improve scoped replay scans,
- deterministic chronology must remain intact across partitions,
- replay tooling must be partition-aware before rollout.

## Operational Migration Requirements
- staged migration with rollback strategy,
- side-by-side validation of replay output parity,
- no partition rollout without observability for partition skew and scan efficiency.
