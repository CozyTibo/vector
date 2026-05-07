# 10-admin Risks

## Phase-Specific Risks
- unsafe replay execution during live traffic
- manual operator actions bypassing controls
- insufficient observability for failure triage
- policy drift across tenants

## Mitigation Expectations
- Detect risk conditions through explicit telemetry.
- Preserve partial truthful outputs under degradation.
- Quarantine unsafe artifacts instead of silently dropping them.
