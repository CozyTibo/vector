# 05-graph Risks

## Phase-Specific Risks
- edge explosion from unbounded relation generation
- cyclic dependency misclassification
- temporal edge conflicts after late-arriving events
- graph reads coupling to synthesis assumptions

## Mitigation Expectations
- Detect risk conditions through explicit telemetry.
- Preserve partial truthful outputs under degradation.
- Quarantine unsafe artifacts instead of silently dropping them.
