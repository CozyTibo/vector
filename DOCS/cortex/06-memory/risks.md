# 06-memory Risks

## Phase-Specific Risks
- aggressive compaction losing critical context
- stale derived memory after upstream replay
- projection divergence across tenants
- query latency spikes from under-indexed derived views

## Mitigation Expectations
- Detect risk conditions through explicit telemetry.
- Preserve partial truthful outputs under degradation.
- Quarantine unsafe artifacts instead of silently dropping them.
