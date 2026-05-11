# Phase 04 — Topology vs Meaning Doctrine

**Status:** normative — **P04-02**.  
**Audience:** implementers, verification authors.  
**Runtime:** `vector.domains.cortex.identity.boundary_checks`.  
**Companion:** `phase-04-architecture-identity-linking-doctrine.md`, `phase-04-anti-goals-doctrine.md`, Phase 03 `ontology.py` (`CanonicalStructuralEdgeKind`), Phase 3.5 `continuity/edge_contracts.py` (`ContinuityEdgeKind`).

---

## 1) Definitions

| Term | Definition |
| ---- | ---------- |
| **Topology (Phase 03)** | Structural projection and **materialization / replay dependency** relationships: canonical object kinds, `CanonicalStructuralEdgeKind`, transform lineage, replay DAG edges, coverage-matrix dependency refs. |
| **Continuity substrate edge (Phase 3.5)** | `ContinuityEdgeContract` — normalized cross-tool **join** envelope; still **not** Phase 04 **org meaning** (no org handles, no merge authority, no “same human”). |
| **Org meaning link (Phase 04)** | Evidence-bound row in the **org link ledger** (future `cortex_org_link`): typed **organizational** relation (e.g. persona→handle, handle→primitive) with policy, temporal validity, and provenance — **disjoint** from topology types. |

**Hard rule:** A Phase 04 org-meaning link payload **must not** encode or smuggle topology as its **link identity** (type or embedded structural arc). Citations **to** materializations/raw as **evidence** are allowed only under explicit keys defined in link-ledger doctrine (future); this document forbids **confusing** topology fields with link type.

---

## 2) Invariants (INV-P04-TOPO-*)

| Id | Statement |
| -- | ----------- |
| **INV-P04-TOPO-01** | `link_type` / `org_link_type` string (if present) MUST NOT equal any `CanonicalStructuralEdgeKind` enum value. |
| **INV-P04-TOPO-02** | Same for any `ContinuityEdgeKind` value — continuity edges are not org meaning link types. |
| **INV-P04-TOPO-03** | Top-level payload MUST NOT include forbidden topology keys (see §4). |
| **INV-P04-TOPO-04** | `source` / `target` endpoint objects (if dicts) MUST NOT carry `structural_edge_kind` or `canonical_structural_edge_kind`. |
| **INV-P04-TOPO-05** | Payload MUST NOT embed a full `ContinuityEdgeContract` at top level (detected via `continuity_edge_contract_version` + `edge_kind` pair at top level). |

---

## 3) Verification gates

| Gate | Role |
| ---- | ---- |
| **G-P04-08** | Topology / continuity-substrate shapes MUST NOT appear as org meaning link payloads (validator + future DB constraint). |
| **G-P04-TOPO-01** | Static harness: `boundary_checks` golden vectors pass/fail as expected (runs inside canonical verification until org verification engine exists). |

Implementation note: **`G-P04-TOPO-01`** is satisfied by the same static gate block as **`G-P04-08`** in the current codebase (single gate id **`G-P04-08`** in `run_canonical_verification`); doctrine text retains both names for doc/traceability.

---

## 4) Forbidden top-level keys (normative set)

Validators MUST reject these keys on the **top-level** org-meaning link payload (extend only via tracker + version bump of `BOUNDARY_CHECKS_VERSION`):

- `structural_edge_kind`
- `canonical_structural_edge_kind`
- `structural_arc`
- `materialization_dag_edge`
- `replay_dependency_edge`
- `transform_lineage_edge`
- `canonical_query_neighbor`

---

## 5) Allowed patterns (informative)

- Explicit lists such as `evidence_raw_record_ids`, `rule_id`, `confidence_posture` (per future link-ledger doctrine).
- Bundle-scoped **canonical pointer** objects as **evidence endpoints**, not as `CanonicalStructuralEdgeKind`.

---

## References

- `phase-04-implementation-plan.md` — P04-02  
- `phase-04-normative-index.md`  
- `backend/src/vector/domains/cortex/identity/boundary_checks.py`  
