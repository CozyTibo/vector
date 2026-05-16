# Phase 07 — Deterministic ranking & selection doctrine

**Status:** normative.  
**NOT:** semantic search, vector similarity, or LLM re-ranking.

---

## Ranking dimensions (integer keys only)

Selection sort key is a **tuple of integers/strings** in fixed priority order — configured per `selection_policy_profile_id`:

| Priority | Dimension | Higher = preferred? | Source field |
| -------- | ----------- | --------------------- | ------------ |
| 1 | `provenance_integrity_rank` | lower rank = better | evidence legality class ordinal |
| 2 | `replay_stability_rank` | lower = better | replay_posture ordinal |
| 3 | `chronology_legality_rank` | lower = better | chronology class ordinal |
| 4 | `continuity_confidence_rank` | lower = better | continuity posture ordinal |
| 5 | `degradation_severity_rank` | lower = better | max `CD-*` severity |
| 6 | `traversal_coverage_rank` | lower = better | hop count / frontier |
| 7 | `recency_legality_rank` | lower = better | `t_as_of` distance (not wall clock) |
| 8 | `evidence_completeness_rank` | lower = better | missing digest count |
| 9 | `tie_break_key` | lexicographic | `materialization_id` / `edge_id` / `walk_id` |

**RULE RET‑RANK‑01:** No floating weights. Policy pack MAY only reorder **integer priority list** — not coefficients.

**RULE RET‑RANK‑02:** **G‑P07‑RANK‑01** static gate rejects JSON keys matching `score`, `weight`, `similarity`, `embedding`.

---

## Bounded retrieval caps

After sort, apply caps → generate omissions (see query contract §6).

---

## Replay equivalence

Given identical:

- query envelope  
- upstream artifact set digests  
- policy digest  

Selection output MUST be byte-identical (**G‑P07‑REPLAY‑01**).

---

## Degradation when ranking truncates

Truncation MUST emit `RD-CAP-HITS` (or specific cap class) with `trigger_count` = overflow count.

---

## Anti-patterns (explicit)

| Anti-pattern | Verdict |
| ------------ | ------- |
| BM25 / TF-IDF relevance | **Forbidden** |
| Learned-to-rank | **Forbidden** |
| “Top-K by embedding distance” | **Forbidden** |
| Random shuffle for diversity | **Forbidden** |
