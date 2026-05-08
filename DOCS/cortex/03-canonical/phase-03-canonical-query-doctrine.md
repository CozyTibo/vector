# Phase 03 — Canonical Query Doctrine (Allowed Classes & Anti-Goals)

**Status:** normative.

## Purpose

Define **supported retrieval intents** for canonical data during Phase 03 without turning canonical retrieval into semantic search, reasoning, or intelligence APIs.

## Supported query classes (conceptual)

| Class | Example intent | Required properties |
| ----- | -------------- | --------------------- |
| **Point lookup** | Fetch canonical entity/event by id | Deterministic, provenance-preserving |
| **Evidence backtrace** | List canonical rows derived from `raw_record_id` | Full lineage visibility |
| **Forward trace** | List raw rows referenced by canonical id | Reverse map indexed |
| **Timeline slice** | Ordered events by time bounds per temporal doctrine | Stable ordering |
| **Graph-local neighborhood** | Bounded hop traversal along evidenced edges | Strict hop/time budgets |
| **Replay/debug** | Diff canonical rebuild vs stored | Divergence classification |

## Forbidden query intents (Phase 03)

- Semantic similarity search (“issues like this”).
- Natural-language Q&A over canonical objects.
- Ranking by inferred importance/urgency.
- “Executive summaries” or stitched narratives across sources.

Those belong to Phase 07+ with explicit product boundaries.

## Graph-safe retrieval semantics

Traversal must:

- Respect tenant isolation,
- Emit truncation markers when budgets exceeded,
- Never infer edges absent from canonical relationship records.

## Replay-aware queries

Queries exposing rebuild comparisons must include:

- `mapping_version_bundle`,
- scope identifiers,
- divergence class summaries.

## References

- Anti-goals: `phase-03-anti-goals-doctrine.md`
- Operator surfaces: `phase-03-canonical-control-plane-doctrine.md`
