# Raw Memory Invariants

## Invariant Contract Table

| Invariant | Meaning | Runtime Check Type | Fail State |
| --------- | ------- | ------------------ | ---------- |
| I1 Raw payload immutability | Raw evidence rows are append-only and non-mutating. | hash drift checks + immutable-row mutation probes | corrupted |
| I2 Provenance reconstructability | Required provenance bootstrap fields are present and linked. | provenance continuity scans | lineage-incomplete / continuity-broken |
| I3 Source identity + revision preservation | Source identity/revision anchors are preserved as observed. | identity/revision continuity checks | degraded / continuity-broken |
| I4 Replay lineage durability | Replay metadata persists and is queryable for replay diagnostics. | replay lineage linkage checks | replay-diverged / lineage-incomplete |
| I5 Deterministic retrieval | Same fixed scope/boundary yields stable evidence ordering/set. | repeatability/replay determinism checks | replay-diverged |
| I6 Temporal ordering determinism | Ordering precedence rules are applied consistently. | temporal ordering validation | reconstruction-limited / degraded |

## Invariant Scope Rule
Invariants apply to preserved evidence semantics only.
They are not semantic-intelligence invariants.
