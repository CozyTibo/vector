# Operational Audit Model

## Audit Scope
- operator actions,
- replay/reprocessing jobs,
- phase state transitions,
- dangerous action approvals and overrides.

## Required Audit Fields
- actor id and role,
- action type and scope,
- timestamp and workspace/tenant context,
- before/after state snapshot references,
- approval chain and reason,
- correlated run/replay identifiers.

## Audit Invariants
- dangerous actions must always be auditable.
- no untracked manual phase mutation.
- audit entries remain immutable.
