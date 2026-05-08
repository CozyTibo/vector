# Raw Memory Retention

## Retention Principles
- retention must preserve minimum replay horizon.
- retention policy must respect tenant governance and deletion requirements.
- retention must not silently break historical reconstruction commitments.
- append-only guarantees apply within retention policy boundaries; no implicit infinite-retention claim.

## Retention Classes
- operational replay horizon,
- long-term audit horizon,
- legal/policy constrained horizon.

## Expiration Handling
- expiration decisions are policy-driven and auditable.
- before deletion/compaction, verify replay obligations are satisfied.
- trust-state impact of expiration must be explicit for affected scopes.

## Tenant Deletion Implications
- tenant-scoped deletion applies across hot and archived raw memory.
- allowed audit metadata retention must remain policy-compliant and non-content-bearing.

## Normative Reference
See `storage-retention-doctrine.md` for operational retention boundary definitions.
