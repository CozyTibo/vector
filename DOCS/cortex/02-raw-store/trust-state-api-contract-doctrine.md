# Phase 02 Trust-State API Contract Doctrine

## Purpose
Define canonical machine-readable trust annotations for runtime responses.

## Contract Principles
- deterministic and machine-parseable,
- scope-explicit (tenant/connector/time/object),
- replay-aware and provenance-aware,
- no semantic interpretation fields.

## Required Response Shape (conceptual)
```json
{
  "scope": {
    "tenant_id": "...",
    "connector": "slack",
    "time_window": {"from": "...", "to": "..."}
  },
  "trust_state": "reconstruction-safe",
  "severity": "S1",
  "state_reason_codes": ["GAP_MISSING_WINDOW"],
  "replay": {"state": "replay-safe", "divergence_class": "none"},
  "reconstruction": {"state": "partial", "coverage_percent": 96.4},
  "provenance": {"state": "lineage-incomplete"},
  "continuity_gaps": [
    {
      "gap_id": "gap-...",
      "type": "missing_evidence_window",
      "window": {"from": "...", "to": "..."},
      "state": "partial"
    }
  ],
  "verification": {"last_verified_at": "...", "gate_results": {"G1": "PASS"}}
}
```

## Required Fields
- `trust_state`,
- `severity`,
- `state_reason_codes`,
- `scope`,
- `verification.last_verified_at`,
- `verification.gate_results`,
- `continuity_gaps` (possibly empty, never omitted).

## Behavior
- `unverifiable`, `replay-diverged`, `continuity-broken`, `corrupted` must include explicit blocking flags.
- absent trust annotation is invalid contract behavior for Phase 02 operator-facing endpoints.
