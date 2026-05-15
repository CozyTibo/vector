# Chronology legality law (Phase 06)

**Status:** constitutional law.

---

## 1. Legality classes

| Class | Meaning |
|-------|---------|
| `chronology_strict` | Total order supported; reasoning may assert strict before/after on this slice. |
| `chronology_partial` | Tie‑breakers applied; some pairwise comparisons undefined — must not assert strict negation. |
| `chronology_unresolved` | Evidence conflict or missing anchor — no total order claim. |
| `chronology_degraded` | Skew / late arrival flagged — bounded derivations only per matrix. |

---

## 2. Downstream gates

When `chronology_unresolved` or `chronology_degraded`, causal chain depth **MUST** cap at **`max_causal_hops_degraded`** from the active [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) and emit **`CD‑CHRON`** on outputs.

---

## 3. Alignment and bridge (authoritative)

**Substrate field:** `TemporalAnchorChain.replay_safe_ordering` ∈ {`strict`,`partial`,`unresolved`} per **`execution_reconstruction_contracts.py`**.  
**Phase 06 projection:** `chronology_legality_class` — **only** via [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md).  
**Forbidden tuples and receipts:** defined there — this law **does not** duplicate the matrix.

---

## 4. Related

[`temporal-reasoning-doctrine.md`](./temporal-reasoning-doctrine.md) · [`temporal-conflict-resolution-law.md`](./temporal-conflict-resolution-law.md)
