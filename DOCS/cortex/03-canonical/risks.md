# 03-canonical Risks

## Phase-Specific Risks
- schema drift causing unstable canonical ids
- tool-specific leakage into canonical taxonomy
- loss of source nuance needed for later replay
- over-normalization hiding important distinctions

## Mitigation Expectations
- Detect risk conditions through explicit telemetry.
- Preserve partial truthful outputs under degradation.
- Quarantine unsafe artifacts instead of silently dropping them.
