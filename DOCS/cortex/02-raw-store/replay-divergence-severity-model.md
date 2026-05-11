# Phase 02 Replay Divergence Severity Model

## Purpose
Classify replay divergence by operational impact.

## Divergence Classes

| Class | Meaning | Severity | Closure Impact | Operational Action |
| ----- | ------- | -------- | -------------- | ------------------ |
| D0 expected_equivalent | no meaningful divergence | S0 | none | normal operation |
| D1 expected_provider_mutation | drift due to documented provider-side mutation | S1 | warn_only/soft_fail depending scope | annotate + monitor |
| D2 expected_schema_reinterpretation | drift due to declared parser/schema version change | S1 | soft_fail until accepted | annotate + approval |
| D3 forbidden_scope_or_order | divergence from scope/order determinism | S2 | hard_fail | block trusted replay publish |
| D4 lineage_breaking_divergence | replay cannot map to preserved lineage guarantees | S2 | hard_fail | quarantine affected scope |
| D5 reconstruction_breaking_divergence | reconstruction guarantees invalidated for required window | S3 | hard_fail | incident + recovery required |

## Policy
- D0-D2 may be tolerated with explicit annotation rules.
- D3-D5 are blocking for Phase 02 closure.
