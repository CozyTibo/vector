# Cross‑system causal continuity (Phase 06)

**Status:** normative law — extends [`../continuity/cross-system-continuity-law.md`](../continuity/cross-system-continuity-law.md) for **TCRE causal** edges.

---

## 1. Continuity strength ordinal (frozen)

Bridge **`S`** is one of **`authoritative` \| `direct` \| `continuity_backed` \| `partial` \| `weak` \| `unverifiable`** per continuity law §5.  
Define **`rank(S)`** (integer, higher = stronger):

| Strength `S` | `rank(S)` |
|--------------|-----------|
| `authoritative` | 6 |
| `direct` | 5 |
| `continuity_backed` | 4 |
| `partial` | 3 |
| `weak` | 2 |
| `unverifiable` | 1 |

**Comparison law:** `S1` is **strictly stronger** than `S2` iff **`rank(S1) > rank(S2)`** — **no** natural‑language comparator.

---

## 2. Cross‑system causal rule (numeric)

Let endpoints have **`connector_origin`** `o_left`, `o_right`.

**CROSS-CAUS-1:** If **`o_left != o_right`**, a **`TCRE`** causal edge that asserts influence across systems **MUST** cite a continuity bridge with:

`rank(S) >= 4` **AND** if `rank(S)==4` then **`IdentityLinkDerivation` ∈ { `explicit_linkage`, `shared_execution_reference` }** per continuity law (same condition as pre‑hardening “`continuity_backed` minimum,” now **ordinal‑closed**).

**CROSS-CAUS-2:** If **`o_left == o_right`**, cross‑system rule does not apply; intra‑system causal edges remain subject to coordination + chronology law only.

---

## 3. Evidence

Both endpoints must list **`NormalizedReference`** equality or explicit URL normalization match in lineage — unchanged from prior spec.

---

## 4. Forbidden

- Causal shortcut on **`temporal_overlap`** alone.  
- Causal merge from Slack tone + Linear title similarity.  
- Using **`rank` partially** (e.g. comparing strings without mapping) — **forbidden**.

---

## 5. Related

[`cross-system-continuity-law.md`](../continuity/cross-system-continuity-law.md) · [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md)
