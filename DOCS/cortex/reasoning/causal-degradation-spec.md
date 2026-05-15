# Causal degradation spec (Phase 06)

**Status:** normative spec.

## Degradation dimensions

| Code | Trigger sketch |
|------|----------------|
| `CD‑CHRON` | `chronology_partial` / `unresolved` caps hops. |
| `CD‑CONT` | Weak or `unverifiable` continuity bridge. |
| `CD‑REPLAY` | Walk / index replay not `replay_equivalent`. |
| `CD‑NEG` | Competing negative signals — partitioned output. |
| `CD‑COMMIT` | Commitment lifecycle contradictory — conflict doctrine path. |

## Receipt

Each degradation entry: `{ code, rule_id, upstream_artifact_ids_sorted, before_hash, after_hash_optional }`.

## Monotonicity

Removing evidence may only **increase** degradation severity or leave unchanged — never silently “heal” without new authoritative evidence.
