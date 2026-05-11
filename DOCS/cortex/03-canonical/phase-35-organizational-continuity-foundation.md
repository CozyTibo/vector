# Phase 3.5 — Organizational Continuity Foundation

**Status:** normative for the Phase 3 → Phase 4 transition.  
**Purpose:** introduce **contracts and deterministic utilities** that shift Cortex from provider-artifact materialization toward **organizational execution continuity reconstruction**, without identity merge, causal inference, or graph storage engines.

**Runtime authority:** `backend/src/vector/domains/cortex/continuity/` (`CONTINUITY_FOUNDATION_SCHEMA_VERSION`, `build_phase35_continuity_public_document`).

---

## 1) Relationship to Phase 03

- Phase 03 remains authoritative for **deterministic transforms**, **bundle-scoped logical keys**, **materialization**, **replay**, **provenance**, and **temporal ordering** within a bundle pin.
- Phase 3.5 adds a **reference plane** and **continuity envelopes** that Phase 04 (identity/linking) and Phase 05 (graph) consume. It does **not** change raw append-only semantics or replay lanes.

---

## 2) Cross-tool reference normalization

### Definition

A **NormalizedReference** is a deterministic, versioned JSON envelope describing a **join handle** derived only from provider-visible fields (or explicit opaque keys). It is **not** a canonical entity and **not** a merged identity.

### Status values

| Status | Meaning |
| ------ | ------- |
| `ok` | Canonical form is stable for joins. |
| `partial` | Explicitly lossy (e.g. short SHA prefix); collision risk acknowledged. |
| `unknown` | Insufficient fields; do not invent. |
| `invalid` | Contradictory or unparsable input. |

### Rules

- **Deterministic:** same inputs → same `canonical_form`.
- **Provenance-preserving:** emitters populate `source_paths` where possible.
- **Bundle-safe:** references do **not** embed `mapping_bundle_id` unless a future rule explicitly scopes a sub-reference (default: bundle-agnostic).
- **Replay-safe:** derived only from raw payload content (or stable raw columns), never from wall-clock inference.

### Implementation

- Schema: `continuity/reference_schema.py`
- Normalization: `continuity/reference_normalize.py`
- Emitters (payload-shaped): `continuity/reference_emitter.py`

---

## 3) Continuity semantics (structural, not narrative)

Phase 3.5 defines **envelopes** for future persistence of:

- execution episodes, ownership transitions, escalation continuity, delivery attempts, workflow/deployment continuity, coordination bursts, blocking chains, review cycles, execution drift markers.

**Forbidden:** NL “stories,” heuristic causality, ML classification of intent.

**Required:** stable keys, explicit evidence raw ids (when materialized later), optional normalized references, optional UTC instants, bundle scope for canonical-adjacent records.

Execution primitive schema: `continuity/execution_primitives.py`.

---

## 4) Graph-ready edge contracts

**ContinuityEdgeContract** is a directed (by default), provenance-bound edge envelope:

- `edge_kind`: closed enum (`ContinuityEdgeKind`)
- `source` / `target`: each may carry `normalized_reference`, `canonical_pointer`, and/or `raw_record_id`
- `confidence_class`: `E0` / `E1` / `E2` (evidence grading; no ranking semantics)
- `evidence_rule_id`: stable deterministic rule identifier
- `bundle_id`, `tenant_id`, optional `temporal_anchor_iso`

**Non-goals:** graph database, traversal engine, AI-generated edges.

Implementation: `continuity/edge_contracts.py`.

---

## 5) Bundle + continuity semantics

Materializations remain **bundle-scoped**. Normalized references are **bundle-agnostic** join keys. Cross-bundle canonical endpoints on a single edge require an explicit **Phase 04 migration / linkage rule** (flagged by `validate_edge_bundle_alignment`).

Implementation: `continuity/bundle_continuity_semantics.py`.

---

## 6) Temporal continuity hardening

Phase 3.5 adds helpers for:

- strict provider timestamp parse status (`ok` / `unknown` / `invalid`)
- explicit **partial order tuple** (occurred, observed, replay sequence, revision, raw id) — no false total order across concurrent provider events
- fallback to existing Phase 03 `build_temporal_ordering_key` for materialization-stable ordering

Implementation: `continuity/temporal_continuity.py`.

---

## 7) Success criteria (Phase 3.5 exit)

- [x] Reference contract + deterministic normalizers + emitters for representative GitHub + Slack payloads.
- [x] Edge contract schema + execution primitive envelopes + bundle semantics rules.
- [x] Temporal helpers aligned with Phase 03 ordering.
- [x] Public JSON document for operator/engine consumption.
- [ ] Persistence layer for edges/primitives (deferred to Phase 04/05; intentionally not in 3.5 code slice unless a separate migration is approved).

---

## 8) Normative index

Listed in `phase-03-normative-index.md` as **XREF** bridging Phase 03 → Phase 04.
