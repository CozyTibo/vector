# Chronology legality law (Phase 06)

**Status:** constitutional law.

## Legality classes

| Class | Meaning |
|-------|---------|
| `chronology_strict` | Total order supported; reasoning may assert strict before/after on this slice. |
| `chronology_partial` | Tie‑breakers applied; some pairwise comparisons undefined — must not assert strict negation. |
| `chronology_unresolved` | Evidence conflict or missing anchor — no total order claim. |
| `chronology_degraded` | Skew / late arrival flagged — bounded derivations only per matrix. |

## Downstream gates

When `chronology_unresolved` or `chronology_degraded`, causal chain depth **MUST** cap at policy `max_causal_hops_degraded` and emit **degradation receipt**.

## Alignment

Must interoperate with `TemporalAnchorChain.replay_safe_ordering` and Phase **05** temporal walk doctrine without contradiction.
