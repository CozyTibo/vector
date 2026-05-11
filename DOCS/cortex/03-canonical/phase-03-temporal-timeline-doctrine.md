# Phase 03 — Temporal & Timeline Doctrine

**Status:** normative.

## Canonical timeline concept

A **canonical timeline** is an ordered set of **canonical events** and **state-transition records** anchored to time fields derived from provider evidence, not inferred narrative.

## Required time roles

| Field role | Description |
| ---------- | ----------- |
| **occurred_at** | Primary domain timestamp when provider evidences event-time |
| **observed_at** | Ingestion/fetch observation when applicable (from Phase 01/02) |
| **canonical_processed_at** | Processing metadata; never substitutes for occurred_at in ordering policy |

## Deterministic ordering precedence (default policy)

When constructing timelines for replay equivalence tests and deterministic sorting:

1. `occurred_at` (UTC-normalized per rule),
2. Provider ordering keys when present (sequence numbers, opaque monotonic tokens),
3. `source_revision_key` / provider version ids from Phase 01 logical keys,
4. `raw_record_id` lexicographic tie-break (never wall-clock random).

Late-arriving evidence interleaves according to precedence above—not operator intuition.

## Retroactive correction semantics

When provider exposes edits as **new revisions** (preferred model aligned with Phase 01 append-only raw):

- Canonical layer emits new canonical version linked to new raw revision,
- Prior canonical projection remains historically accessible via supersession.

## Phase 03 vs causal reasoning

Ordering **is not** causal inference. It is **sort stability** and **reconstructability**. Causality belongs to Phase 06+.

---

## Runtime temporal continuity

### Late-arriving evidence

When new raw revisions arrive after prior canonicalization:

- Emit new canonical revision linked to new raw id; supersede prior canonical projection per replay doctrine,
- Maintain ordering determinism—**do not** reshuffle historical ordering keys retroactively except via explicit supersession chains.

### Supersession chains

- Each supersession MUST reference predecessor canonical id + causing raw id + bundle id.

### Revision chains (cross-phase alignment)

- Align with Phase 02 revision index semantics: canonical ordering uses provider timestamps / revision keys when present (`phase-03-replay-versioning-doctrine.md` inputs).

### Rebuild ordering consistency

Rebuild passes MUST sort/process raw inputs in **canonical deterministic ingest order** (declared ordering key over raw cursor)—never nondeterministic parallel merge without reduction proof.

### Timeline determinism

Two rebuilds with identical inputs produce **identical ordered event sequences** under temporal tests—otherwise classify as C4 failure.

## References

- Replay equivalence: `phase-03-replay-versioning-doctrine.md`
- Ambiguity when timestamps missing: `phase-03-ambiguity-confidence-doctrine.md`
- Logical keys (tie-break): `phase-03-logical-key-doctrine.md`
