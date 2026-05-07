# 04-entity-resolution Risks

## Phase-Specific Risks
- false merges causing long-lived graph corruption
- identity churn from unstable heuristics
- low-confidence links consumed as truth
- cross-tenant identity leakage

## Mitigation Expectations
- Detect risk conditions through explicit telemetry.
- Preserve partial truthful outputs under degradation.
- Quarantine unsafe artifacts instead of silently dropping them.
