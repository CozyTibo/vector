# Phase State Model

## Phase States
- `HEALTHY`
- `DEGRADED`
- `REPLAYING`
- `PARTIAL_FAILURE`
- `THROTTLED`
- `RECOVERING`
- `AMBIGUOUS`
- `STALLED`
- `CORRUPTED`
- `QUARANTINED`

## Transition Rules
- `HEALTHY -> DEGRADED` on sustained error/lag signals.
- `DEGRADED -> RECOVERING` on active remediation.
- `RECOVERING -> HEALTHY` on verification pass.
- `ANY -> CORRUPTED` on integrity-critical failures.
- `CORRUPTED -> QUARANTINED` for containment workflow.
- `HEALTHY|DEGRADED -> REPLAYING` via replay control path.

## Operator Visibility
Every state must expose:
- trigger reason,
- impacted scopes,
- downstream risks,
- recommended next actions.
