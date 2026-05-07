# 02-raw-store Risks

## Phase-Specific Risks
- storage growth outpacing index maintenance
- accidental mutability via update paths
- insufficient replay pointers for targeted rebuilds
- retention policy conflicts across tenants

## Mitigation Expectations
- Detect risk conditions through explicit telemetry.
- Preserve partial truthful outputs under degradation.
- Quarantine unsafe artifacts instead of silently dropping them.
