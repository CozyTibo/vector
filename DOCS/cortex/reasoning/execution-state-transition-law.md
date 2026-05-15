# Execution state transition law (Phase 06)

**Status:** constitutional law.

## State machine (conceptual)

States are **execution coordination states** derived from contracts — e.g. `open_ask`, `blocked`, `escalated_active`, `commitment_active`, `silence_window_open` — exact enum frozen at implementation.

## Transitions

Each transition requires:

- Trigger event id(s) or negative signal id(s).  
- `derivation_rule_id`.  
- Optional `guard` expression evaluated deterministically (no float math).

## Forbidden

Implicit transition from silence to “cancelled” without explicit evidence or policy `rule_id`.

## Alignment

Maps to `ExecutionThreadState` fields and `CommitmentLifecycleState` transitions without inventing new lifecycle enums silently.
