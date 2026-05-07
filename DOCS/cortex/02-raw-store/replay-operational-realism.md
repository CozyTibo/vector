# Replay Operational Realism

## Operational Replay Modes
| Mode | Typical Scope | Operational Use |
| ---- | ------------- | --------------- |
| Scoped replay | Tenant + connector + bounded window | Default trust-recovery path. |
| Partial replay | Tenant + phase-limited dependency scope | Targeted correction after extractor/mapper change. |
| Broad replay | Multi-window historical range | Exceptional use only; high cost. |

## Realistic Replay Pressure Points
- replay scan sizes grow superlinearly when scope filters are weak,
- queue pressure increases sharply under concurrent tenant replay,
- cold archive rehydration can dominate replay wall-clock,
- replay jobs can starve live ingestion without explicit lane isolation.

## Replay Throughput Assumptions (Operational)
- scoped replay should be first-class and quota-protected,
- broad replay should require explicit approval and budget check,
- replay queue should have priority tiers (critical fix > routine refresh),
- replay job planner should estimate scan volume before dispatch.

## Replay Storage And Indexing Reality
- replay is selector-heavy, not just throughput-heavy,
- chronology + tenant + connector indexes are mandatory,
- replay job lineage keys are required for deterministic diagnostics,
- index bloat risk is real if replay and forensic indexes are both expanded blindly.

## Tenant Isolation Requirements
- per-tenant replay concurrency caps,
- tenant-fair scheduling to avoid noisy-neighbor replay starvation,
- separate accounting for replay resource usage by tenant.

## Operational Guardrails
1. Default to scoped replay.
2. Enforce max replay window per normal job.
3. Require dry-run estimate for broad replay.
4. Pause/slow replay when ingestion protection threshold is breached.
5. Expose replay lag, queue depth, and rehydration latency in operator UI.
