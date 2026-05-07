# 01-ingestion Risks

## Phase-Specific Risks
- connector API drift silently breaking extraction
- rate-limit storms during backfill
- duplicate fetch windows causing downstream event inflation
- clock skew in source timestamps

## Mitigation Expectations
- Detect risk conditions through explicit telemetry.
- Preserve partial truthful outputs under degradation.
- Quarantine unsafe artifacts instead of silently dropping them.
