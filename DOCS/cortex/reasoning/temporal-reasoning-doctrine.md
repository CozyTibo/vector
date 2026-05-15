# Temporal reasoning doctrine (Phase 06)

**Status:** constitutional doctrine.  
**Defines:** lawful **temporal substrate** for execution reconstruction — intervals, anchors, stitching, degradation — **without** inventing timestamps or narrative timelines.

## Inputs (authoritative only)

- `TemporalAnchor`, `TemporalAnchorChain`, `ExecutionInteractionWindow`, `ExecutionChronologyWindow`, `CrossSourceTemporalReference` from `execution_reconstruction_contracts.py`.  
- Phase **05** `temporal_anchor` total order law where walk receipts participate.  
- Raw connector timestamps + monotonic export cursors.

## Outputs (bounded)

- Declared **replay_safe_ordering** for reasoning slices (`strict` | `partial` | `unresolved`).  
- Half‑open **interval graphs** for obligations, silence, dependency wait — all **derivation_rule_id** tagged.  
- **Chronology degradation receipts** when skew or late arrival prevents strict order.

## Invariants

**T‑TEMP‑01:** No reasoning interval without ≥1 anchor or raw id in lineage.  
**T‑TEMP‑02:** Late arrival **never** rewrites committed historical labels; it appends superseding evidence with new ids.  
**T‑TEMP‑03:** Cross‑system reconciliation uses only `cross-system-continuity-law.md` linkage classes.

## Non‑goals

Imputing missing user event times, “business day” adjustments without pinned policy id, semantic “timeline summary.”
