# Temporal conflict resolution law (Phase 06)

**Status:** constitutional law — **temporal specialization** of `../continuity/conflict-resolution-doctrine.md`.

## Applicable conflict classes

`chronology_conflict`, `export_sequence_conflict`, anchor skew, late‑arrival vs export order.

## Precedence

1. Immutable connector native timestamp when present.  
2. Monotonic export cursor.  
3. Ingestion `fetched_at` tie‑break only with explicit `rule_id`.  
4. Otherwise `chronology_unresolved` + degradation.

## Outcomes

Never emit `chronology_strict` if any pairwise comparison remains undefined without documented tie‑break.

## Receipts

Every resolution emits `reasoning_chronology_receipt` delta or append‑only correction row.
