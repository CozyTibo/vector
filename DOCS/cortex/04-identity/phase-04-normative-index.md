# Phase 04 — Normative index (Identity & Linking)

**Status:** registry + vocabulary anchor — **individual doctrine files listed below are not all authored yet**; authoritative sequencing and gate drafts live in `phase-04-implementation-plan.md`.  
**Role:** single entry point for Phase 04 normative work; prevents split-brain naming across runtime, DB, verification, and admin.

---

## Document hierarchy

| Document | Role |
| -------- | ---- |
| `phase-04-architecture-identity-linking-doctrine.md` | End-state architecture, boundaries, executive GO/NO-GO framing |
| `phase-04-implementation-plan.md` | **22-stage program (P04-01–P04-22)**, persistence/runtime inventory, gate list **G-P04-01–G-P04-26**, closure |
| `phase-04-control-plane-doctrine.md` | **Execution Continuity Operator Console** — admin IA, mandatory surfaces, HTTP §15 inventory, JSON contracts, **G-P04-21–G-P04-26** |
| `phase-04-mock-data-strategy.md` | **Hostile continuity mock dataset** — deterministic scenarios (`P04MD-*`, `nexora_p04_*`), personas, L-class drift, CI slices, generator guidance (`backend/mock_connectors/`) |
| This file | Index, stage↔doctrine map, vocabulary, **status** of each planned doctrine |

---

## Vocabulary (non-negotiable distinctions)

| Term | Meaning |
| ---- | ------- |
| **Org handle / org entity** | Tenant-scoped organizational identity carrier — **not** a Phase 03 canonical row id |
| **Topology / materialization edge** | Phase 03 transform/replay structure — **must not** appear as authoritative org meaning |
| **Meaning link** | Typed, evidence-bound row in the **link ledger** (Phase 04) |
| **Candidate link** | Regenerated suggestion — **never** authoritative until promoted under policy |
| **Authoritative link** | Ledger-backed truth for org continuity (replay from ledger) |
| **Hint** | “Might be related” — **excluded** from merge closure |
| **Merge record** | Governed equivalence of org handles — **not** implied by reference normalization |
| **Execution primitive instance** | Org-shaped span/episode bound to evidence (see execution primitive doctrine) |
| **Execution Continuity Operator Console** | Phase 04 admin substrate: sparse, table-first, evidence/replay-first surfaces per `phase-04-control-plane-doctrine.md` — **not** Phase 09 product UI |

---

## Stage program ↔ primary doctrine outputs

| Stage | Title | Primary doctrine / artifact (planned filename) |
| ----- | ----- | ---------------------------------------------- |
| P04-01 | Normative index + program freeze | **This file** + `phase-04-anti-goals-doctrine.md` (optional merge into index) |
| P04-02 | Topology vs meaning boundary | `phase-04-topology-vs-meaning-doctrine.md` |
| P04-03 | Org handle + org entity | `phase-04-org-entity-and-handle-doctrine.md` |
| P04-04 | Link ledger | `phase-04-link-ledger-doctrine.md` |
| P04-05 | Candidate vs authoritative | `phase-04-candidate-vs-authoritative-linkage-doctrine.md` |
| P04-06 | Merge governance | `phase-04-merge-governance-doctrine.md` |
| P04-07 | Hint / inferred / prohibited | `phase-04-hint-and-prohibited-link-doctrine.md` |
| P04-08 | Temporal validity + revocation | `phase-04-temporal-validity-and-revocation-doctrine.md` |
| P04-09 | Bundle + cross-bundle equivalence | `phase-04-cross-bundle-equivalence-doctrine.md` |
| P04-10 | Continuity replay + regeneration | `phase-04-continuity-replay-doctrine.md` |
| P04-11 | Linkage rule engine + versioning | `phase-04-linkage-rule-engine-doctrine.md` |
| P04-12 | Execution primitive persistence | `phase-04-execution-primitive-persistence-doctrine.md` |
| P04-13 | Graph boundary + P05 export | `phase-04-graph-boundary-doctrine.md` + `phase-04-graph-projection-export-doctrine.md` |
| P04-14 | Ambiguity + multiplicity (org) | `phase-04-ambiguity-multiple-persona-doctrine.md` |
| P04-15 | Verification engine (org extension) | `phase-04-verification-gates-doctrine.md` (normative gate IDs) |
| P04-16 | Failure + remediation (org) | `phase-04-failure-remediation-doctrine.md` |
| P04-17 | Control plane aggregate | `phase-04-control-plane-doctrine.md` |
| P04-18 | API routes | `phase-04-control-plane-doctrine.md` **§15** route inventory + §16 list contracts (OpenAPI appendix lives with control plane doc) |
| P04-19 | Celery / worker jobs | `phase-04-continuity-replay-doctrine.md` §jobs + control plane |
| P04-20 | Migration + backfill | `phase-04-backfill-doctrine.md` |
| P04-21 | Stabilization + economics | `phase-04-readiness-audit.md` (economics section) |
| P04-22 | Closure + certification | `phase-04-closure-gates-doctrine.md` |

**Likely additional doctrines** (see implementation plan §5): privacy/minimization, authorization for merges, tenant isolation — add rows here when accepted.

---

## Doctrine file inventory (authorship status)

Legend: **Shipped** = file exists under `DOCS/cortex/04-identity/` and is referenced as normative. **Planned** = specified in program only.

| File | Status |
| ---- | ------ |
| `phase-04-normative-index.md` | **Shipped** (this file) |
| `phase-04-architecture-identity-linking-doctrine.md` | **Shipped** |
| `phase-04-implementation-plan.md` | **Shipped** |
| `phase-04-topology-vs-meaning-doctrine.md` | Planned |
| `phase-04-org-entity-and-handle-doctrine.md` | Planned |
| `phase-04-link-ledger-doctrine.md` | Planned |
| `phase-04-merge-governance-doctrine.md` | Planned |
| `phase-04-candidate-vs-authoritative-linkage-doctrine.md` | Planned |
| `phase-04-temporal-validity-and-revocation-doctrine.md` | Planned |
| `phase-04-cross-bundle-equivalence-doctrine.md` | Planned |
| `phase-04-continuity-replay-doctrine.md` | Planned |
| `phase-04-linkage-rule-engine-doctrine.md` | Planned |
| `phase-04-execution-primitive-persistence-doctrine.md` | Planned |
| `phase-04-graph-projection-export-doctrine.md` | Planned |
| `phase-04-hint-and-prohibited-link-doctrine.md` | Planned |
| `phase-04-ambiguity-multiple-persona-doctrine.md` | Planned |
| `phase-04-verification-gates-doctrine.md` | Planned |
| `phase-04-failure-remediation-doctrine.md` | Planned |
| `phase-04-control-plane-doctrine.md` | **Shipped** (Execution Continuity Operator Console — IA, surfaces, routes, contracts, **G-P04-21–G-P04-26**) |
| `phase-04-backfill-doctrine.md` | Planned |
| `phase-04-readiness-audit.md` | Planned |
| `phase-04-closure-gates-doctrine.md` | Planned |
| `phase-04-anti-goals-doctrine.md` | Planned (may fold into this index) |
| `phase-04-graph-boundary-doctrine.md` | Planned |
| `phase-04-mock-data-strategy.md` | **Shipped** (mock/fixture normative strategy — see implementation plan §13.1, P04-20) |

---

## Verification gates (canonical list)

Normative numbering and acceptance criteria: **`phase-04-implementation-plan.md` §12.1** (**G-P04-01** through **G-P04-26**). Operator-console gates **G-P04-21–G-P04-26** are defined in **`phase-04-control-plane-doctrine.md` §18**. This index does not duplicate gate text — avoid drift.

---

## GO / NO-GO (runtime)

Per **`phase-04-implementation-plan.md` §20** and **`phase-04-architecture-identity-linking-doctrine.md`** final section: **NO-GO** to coding until topology≠meaning is verification-enforced, merge/hint/candidate/authoritative classes are frozen, and cross-bundle equivalence is specified.

---

## Upstream / downstream

- **Upstream:** Phase 01–03, Phase 3.5 `phase-35-organizational-continuity-foundation.md`, `vector.domains.cortex.continuity`.
- **Downstream:** Phase 05 consumes **`OrgGraphProjectionV1`** (export contract in implementation plan §18) — **no** graph traversal engine in Phase 04.
