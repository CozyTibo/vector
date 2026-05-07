# Raw Storage Indexing

## Index Priority Tiers
| Tier | Purpose | Policy |
| ---- | ------- | ------ |
| Tier 1 (Critical) | Replay determinism + integrity verification | Mandatory, high-protection from pruning. |
| Tier 2 (Operational) | Forensic and operator diagnostics | Keep if query-owned and actively used. |
| Tier 3 (Optional) | Convenience lookups | Remove aggressively if write cost > value. |

## Replay-Critical Indexes (Tier 1)
- tenant + connector + source chronology,
- replay job selector + chronology ordering,
- source identity lookup selectors,
- idempotency uniqueness constraints.

## Chronology And Scope Indexes (Tier 1-2)
- source occurrence timestamp selectors,
- observed/created time selectors for operational windows,
- tenant/connector scope selectors for isolation.

## Archival/Integrity Indexes (Tier 1)
- archival pointer lookup keys,
- integrity hash verification selectors.

## Operational Index Policy
- every index must have an owning query class,
- index additions require expected write-amplification impact review,
- quarterly pruning of low-value optional indexes,
- replay and integrity indexes cannot be dropped without explicit review gate.
