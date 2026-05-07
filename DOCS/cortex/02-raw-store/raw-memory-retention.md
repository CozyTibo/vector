# Raw Memory Retention

## Retention Principles
- retention must preserve minimum replay horizon.
- retention policy must respect tenant governance and deletion requirements.
- retention must not silently break historical reconstruction commitments.

## Retention Classes
- operational replay horizon,
- long-term audit horizon,
- legal/policy constrained horizon.

## Expiration Handling
- expiration decisions are policy-driven and auditable.
- before deletion/compaction, verify replay obligations are satisfied.

## Tenant Deletion Implications
- tenant-scoped deletion applies across hot and archived raw memory.
- allowed audit metadata retention must remain policy-compliant and non-content-bearing.
