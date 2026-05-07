# 08-retrieval Risks

## Phase-Specific Risks
- context packs omitting critical contradictory evidence
- permission bugs leaking restricted artifacts
- ranking bias toward recent events only
- retrieval latency collapse under high fanout

## Mitigation Expectations
- Detect risk conditions through explicit telemetry.
- Preserve partial truthful outputs under degradation.
- Quarantine unsafe artifacts instead of silently dropping them.
