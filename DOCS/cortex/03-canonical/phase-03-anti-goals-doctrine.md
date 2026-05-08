# Phase 03 — Anti-Goals Doctrine (Semantic / AI / Managerial Creep)

**Status:** normative for Phase 03.  
**Audience:** spec authors, implementers, reviewers, operators.

## Purpose

Phase 03 is **structural normalization + deterministic linking** from Phase 02 raw organizational memory to canonical organizational primitives. This document defines **hard anti-goals** so implementation cannot drift into cognition, interpretation, or opaque scoring.

## Absolute prohibitions (Phase 03)

Phase 03 runtime and canonical outputs **must not**:

- Infer **business meaning**, strategic intent, urgency, priority, or managerial interpretation.
- Infer **ownership semantics** beyond explicitly evidenced structural fields (see deterministic doctrine for what counts as evidence).
- Infer **blockers**, **risk**, **deadlines**, **success likelihood**, or **execution quality**.
- Generate **summaries**, **narratives**, **recommendations**, **rankings**, **predictions**.
- Perform **semantic search**, **embedding retrieval**, **LLM reasoning**, or **AI synthesis** as part of canonicalization proper.
- Collapse **ambiguity** into a single winner without an explicit, auditable resolution record (policy-driven or evidence-driven in later phases—not silent).
- Introduce **hidden heuristics** that change canonical outputs without version visibility and provenance.
- Perform **irreversible canonical mutation** that destroys reversibility to raw evidence (mutation must remain explainable as supersession/versioning per replay doctrine).

## Allowed adjacent techniques (only with strict containment)

If future slices introduce **deterministic** machine-assisted labeling (explicitly out of scope for initial Phase 03 runtime unless a gate permits it), such techniques remain **forbidden in Phase 03** unless/until:

- They are **optional**, **off-by-default**, and isolated behind explicit Phase 03 closure gates,
- Every output field is tagged with **evidence-grade** vs **machine-labeled** provenance,
- Ambiguity and contesting outputs are preserved per ambiguity doctrine,
- Replay semantics remain deterministic per replay doctrine.

**Default posture:** Phase 03 ships **without** ML/LLM in the canonicalization hot path.

## Semantic creep detectors (review checklist)

Treat any of the following as a **spec violation** until moved to a later phase or explicitly neutralized:

- Natural-language fields that encode interpretation (“likely blocker”, “appears urgent”).
- Scores without an explicit deterministic formula reference in doctrine.
- Unified “importance” or “impact” dimensions.
- Graph intelligence queries exposed as canonical queries (see canonical query doctrine).

## Canonical admin / control-plane anti-goals (explicit)

Phase 03 operator surfaces MUST remain **operational substrate visibility**. Forbidden admin UX/spec patterns:

- **Semantic dashboards** — thematic insights, “org health stories,” interpreted trends beyond substrate counters.
- **AI-generated canonical explanations** — LLM text explaining why something “matters” organizationally.
- **Managerial interpretation** — ownership/blocker/priority narratives not evidenced as structured fields.
- **Execution insights** — delivery velocity, team performance, risk narratives.
- **Graph cognition** — traversal products framed as intelligence (Phase 05+), not structural neighbor listing under bounded queries.
- **Inferred organizational meaning** — NL labels implying intent (“escalated,” “critical”) without deterministic rule ids.
- **Non-deterministic trust scoring** — opaque composite scores; allowed labels are **stale/fresh**, **PASS/FAIL**, **C-class**, **explicit ambiguity density**, tied to receipts.

Canonical admin shows **deterministic proof artifacts** (bundle ids, gate matrices, lineage pointers, job receipts)—see `phase-03-canonical-control-plane-doctrine.md`.

## Relationship to other doctrines

- Deterministic boundaries: `phase-03-deterministic-canonicalization-doctrine.md`
- Ambiguity must persist visibly: `phase-03-ambiguity-confidence-doctrine.md`
- Operator visibility + mandatory surfaces: `phase-03-canonical-control-plane-doctrine.md`

## Non-goals explicitly owned by later phases

| Forbidden in Phase 03 | Typical owning phase |
| --------------------- | -------------------- |
| Cross-tool identity equivalence decisions | Phase 04 |
| Organizational graph intelligence | Phase 05+ |
| Causal/temporal reasoning beyond ordering doctrine | Phase 06+ |
| Retrieval products | Phase 07+ |
| Synthesis / operator copilots | Phase 08+ |
