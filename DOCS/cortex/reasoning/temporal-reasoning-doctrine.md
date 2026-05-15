# Temporal reasoning doctrine (Phase 06)

**Status:** constitutional doctrine.  
**Defines:** lawful **temporal substrate** for execution reconstruction — intervals, anchors, stitching, degradation — **without** inventing timestamps or narrative timelines.

---

## 1. Inputs (authoritative only)

- `TemporalAnchor`, `TemporalAnchorChain`, `ExecutionInteractionWindow`, `ExecutionChronologyWindow`, `CrossSourceTemporalReference` from `execution_reconstruction_contracts.py`.  
- Phase **05** `temporal_anchor` total order law where walk receipts participate.  
- Raw connector timestamps + monotonic export cursors.

---

## 2. Outputs (bounded)

- **Read‑only consumption** of **`TemporalAnchorChain.replay_safe_ordering`** — Phase **06** **MUST NOT** mutate this field in place.  
- **Derived** **`chronology_legality_class`** per [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md) + active [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md).  
- Half‑open **interval graphs** for obligations, silence, dependency wait — all **`derivation_rule_id`** tagged.  
- **`reasoning_chronology_receipt`** when projection or intervals emit.

---

## 3. Invariants

**T‑TEMP‑01:** No reasoning interval without ≥1 anchor or raw id in lineage.  
**T‑TEMP‑02:** Late arrival **never** rewrites committed historical labels; it appends superseding evidence with new ids.  
**T‑TEMP‑03:** Cross‑system reconciliation uses only `cross-system-continuity-law.md` linkage classes.

---

## 4. Non‑goals

Imputing missing user event times, “business day” adjustments without pinned policy id, semantic “timeline summary.”
