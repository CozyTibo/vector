# Causal degradation spec (Phase 06)

**Status:** normative spec.

---

## 1. Degradation codes (`CD‑*`)

| Code | Trigger sketch |
|------|----------------|
| `CD‑CHRON` | `chronology_partial` / `chronology_unresolved` / `chronology_degraded` per state machine; hop caps from policy pack. |
| `CD‑CONT` | Continuity bridge `rank(S) < 4` for cross‑system causal, or `unverifiable`. |
| `CD‑REPLAY` | Walk / index replay not `replay_equivalent`; includes **`replay_conflicted`**. |
| `CD‑NEG` | Competing negative signals — partitioned output. |
| `CD‑COMMIT` | Commitment lifecycle contradictory — conflict doctrine path. |

---

## 2. Global severity ordinal (monotonicity)

Define **`severity_rank(CD‑*)`** for monotonic comparisons:

| Code | `severity_rank` |
|------|-----------------|
| `CD‑COMMIT` | 5 |
| `CD‑REPLAY` | 4 |
| `CD‑NEG` | 4 |
| `CD‑CHRON` | 3 |
| `CD‑CONT` | 2 |

**Law DEG‑MON‑1:** When multiple codes apply, **sort** by **`(-severity_rank, code, rule_id)`** for stable display; **monotonic removal of evidence** may only **increase** the multiset of codes under the product order (no silent heal).

---

## 3. Corpus string alignment (golden thread)

`expected_degradation_classes` in corpus **MUST** normalize to **`CD‑*`** or these **approved aliases** (loaders map left → right):

| Corpus alias (legacy / operator) | Canonical |
|----------------------------------|-----------|
| `replay_skew` | `CD‑REPLAY` |
| `stale_verification` | `CD‑REPLAY` |
| `chronology_cap_applied` | `CD‑CHRON` |
| `continuity_bridge_weak` | `CD‑CONT` |
| `partitioned_negative_signal` | `CD‑NEG` |
| `commitment_lifecycle_conflict` | `CD‑COMMIT` |

**G‑P06‑DEG‑01:** Unknown strings **fail** corpus validation.

---

## 4. Receipt

Each degradation entry: `{ "code", "rule_id", "upstream_artifact_ids_sorted", "before_hash", "after_hash_optional" }` — sorted list order by `(code, rule_id)`.

---

## 5. Provenance law alignment

Replace coarse **`degradation_semantics`** labels on artifacts with **sorted `CD‑*`** list + optional coarse tag **`none` \| `composite`** where **`composite`** means `|codes| > 1` — see [`reasoning-provenance-law.md`](./reasoning-provenance-law.md).

---

## 6. Monotonicity (evidence removal)

Removing evidence may only **increase** applicable **`severity_rank`** or add codes — never silently remove a **`CD‑*`** without new authoritative supersession per [`../continuity/conflict-resolution-doctrine.md`](../continuity/conflict-resolution-doctrine.md).
