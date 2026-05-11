# Phase 04 — Normative index (Identity & Linking)

**Status:** registry + vocabulary anchor — **P04-01 frozen** (see §Program freeze). Individual runtime doctrine files listed below are not all authored yet; authoritative sequencing and gate drafts live in `phase-04-implementation-plan.md`.  
**Role:** single entry point for Phase 04 normative work; prevents split-brain naming across runtime, DB, verification, and admin.

---

## Program freeze (P04-01)

| Field | Value |
| ----- | ----- |
| **PHASE04_PROGRAM_FREEZE_VERSION** | `1` (must match `vector.domains.cortex.identity.normative.PHASE04_PROGRAM_FREEZE_VERSION`) |
| **Scope** | Normative index, vocabulary, document hierarchy, doctrine inventory, anti-goals doctrine, cross-links to implementation plan + architecture + control plane + mock strategy |
| **Runtime** | `vector.domains.cortex.identity` package exists with **metadata only** (`normative.py`); no linkage engine until P04-02+ |

**Frozen in this version:** glossary terms §Vocabulary; stage map P04-01–P04-22; gate list pointer **G-P04-01–G-P04-26**; anti-goals in `phase-04-anti-goals-doctrine.md`.

---

## Document hierarchy

| Document | Role |
| -------- | ---- |
| `phase-04-architecture-identity-linking-doctrine.md` | End-state architecture, boundaries, executive GO/NO-GO framing |
| `phase-04-anti-goals-doctrine.md` | **Non-negotiable** Phase 04 anti-goals (layer + identity + integrity + operator UX) |
| `phase-04-topology-vs-meaning-doctrine.md` | Topology vs org-meaning boundary, **INV-P04-TOPO-***, **G-P04-08** / static harness |
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
| **Persona binding** | Temporal association of a provider-scoped persona to an org handle — evidence-bound; not automatic identity |
| **Normalized reference** | Phase 3.5 reference plane / `canonical_form` — **join key**, not proof of “same human” |
| **Link ledger** | Append-only or event-sourced store of **meaning links** (authoritative rows + metadata), distinct from Phase 03 topology |
| **Two-layer replay** | **Candidate** regeneration (rule-version pinned) vs **authoritative** replay from ledger — both required |
| **OrgGraphProjectionV1** | Frozen export contract for Phase 05 — **not** a traversal engine or admin graph UI |
| **Bundle equivalence declaration** | Explicit record allowing cross-bundle canonical endpoints on org edges; absent → blocked or ambiguous |
| **Drift class (L-class)** | Phase 04 link/regen divergence taxonomy (e.g. L1–L7 in mock strategy); receipt-backed |

---

## Stage program ↔ primary doctrine outputs

| Stage | Title | Primary doctrine / artifact (planned filename) |
| ----- | ----- | ---------------------------------------------- |
| P04-01 | Normative index + program freeze | **This file** + `phase-04-anti-goals-doctrine.md` (**Shipped**) |
| P04-02 | Topology vs meaning boundary | `phase-04-topology-vs-meaning-doctrine.md` (**Shipped**) + `vector.domains.cortex.identity.boundary_checks` |
| P04-03 | Org handle + org entity | `phase-04-org-entity-and-handle-doctrine.md` (**Shipped**) |
| P04-04 | Link ledger | `phase-04-link-ledger-doctrine.md` (**Shipped**) |
| P04-05 | Candidate vs authoritative | `phase-04-candidate-vs-authoritative-linkage-doctrine.md` (**Shipped**) |
| P04-06 | Merge governance | `phase-04-merge-governance-doctrine.md` (**Shipped**) |
| P04-07 | Hint / inferred / prohibited | `phase-04-hint-and-prohibited-link-doctrine.md` (**Shipped**) |
| P04-08 | Temporal validity + revocation | `phase-04-temporal-validity-and-revocation-doctrine.md` (**Shipped**) |
| P04-09 | Bundle + cross-bundle equivalence | `phase-04-cross-bundle-equivalence-doctrine.md` (**Shipped**) |
| P04-10 | Continuity replay + regeneration | `phase-04-continuity-replay-doctrine.md` (**Shipped**) + `vector.domains.cortex.identity.org_link_replay_runtime` |
| P04-11 | Linkage rule engine + versioning | `phase-04-linkage-rule-engine-doctrine.md` (**Shipped**) + `vector.domains.cortex.identity.linkage_rules` |
| P04-12 | Execution primitive persistence | `phase-04-execution-primitive-persistence-doctrine.md` (**Shipped**) + `vector.domains.cortex.identity.execution_primitives` |
| P04-13 | Graph boundary + P05 export | `phase-04-graph-boundary-doctrine.md` (**Shipped**) + `phase-04-graph-projection-export-doctrine.md` (**Shipped**) + `vector.domains.cortex.identity.projection_export` |
| P04-14 | Ambiguity + multiplicity (org) | `phase-04-ambiguity-multiple-persona-doctrine.md` (**Shipped**) + `vector.domains.cortex.identity.org_ambiguity` |
| P04-15 | Verification engine (org extension) | `phase-04-verification-gates-doctrine.md` (**Shipped**) + `vector.domains.cortex.identity.verification` + **`cortex_org_verification_runs`** |
| P04-16 | Failure + remediation (org) | `phase-04-failure-remediation-doctrine.md` (**Shipped**) + `vector.domains.cortex.identity.failure_remediation` + **`cortex_org_failure_cases`** / **`cortex_org_remediation_validations`** |
| P04-17 | Control plane aggregate | `phase-04-control-plane-doctrine.md` (**Shipped** runtime slice) + **`vector.domains.cortex.identity.control_plane`** + **G-P04-18** / **G-P04-21** + **`GET .../identity/control-plane`** |
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
| `phase-04-topology-vs-meaning-doctrine.md` | **Shipped** (P04-02; `boundary_checks`, **G-P04-08** in canonical verification) |
| `phase-04-org-entity-and-handle-doctrine.md` | **Shipped** (P04-03) |
| `phase-04-link-ledger-doctrine.md` | **Shipped** (P04-04) |
| `phase-04-candidate-vs-authoritative-linkage-doctrine.md` | **Shipped** (P04-05) |
| `phase-04-merge-governance-doctrine.md` | **Shipped** (P04-06) |
| `phase-04-hint-and-prohibited-link-doctrine.md` | **Shipped** (P04-07) |
| `phase-04-temporal-validity-and-revocation-doctrine.md` | **Shipped** (P04-08) |
| `phase-04-cross-bundle-equivalence-doctrine.md` | **Shipped** (P04-09) |
| `phase-04-continuity-replay-doctrine.md` | **Shipped** (P04-10) |
| `phase-04-linkage-rule-engine-doctrine.md` | **Shipped** (P04-11) |
| `phase-04-execution-primitive-persistence-doctrine.md` | **Shipped** (P04-12) |
| `phase-04-graph-projection-export-doctrine.md` | **Shipped** (P04-13) |
| `phase-04-ambiguity-multiple-persona-doctrine.md` | **Shipped** (P04-14) |
| `phase-04-verification-gates-doctrine.md` | **Shipped** (P04-15) |
| `phase-04-failure-remediation-doctrine.md` | **Shipped** (P04-16; `failure_remediation`, **G-P04-19**, org failure tables) |
| `phase-04-control-plane-doctrine.md` | **Shipped** (Execution Continuity Operator Console — IA, surfaces, routes, contracts, **G-P04-21–G-P04-26**) |
| `phase-04-backfill-doctrine.md` | **Shipped** (P04-20) |
| `phase-04-readiness-audit.md` | **Shipped** (P04-21; economics probes + **G-P04-ECO-01**) |
| `phase-04-closure-gates-doctrine.md` | **Shipped** (P04-22; **G-P04-CLOSE-01** + org certification pack) |
| `phase-04-anti-goals-doctrine.md` | **Shipped** (P04-01; non-negotiable anti-goals) |
| `phase-04-graph-boundary-doctrine.md` | **Shipped** (P04-13) |
| `phase-04-mock-data-strategy.md` | **Shipped** (mock/fixture normative strategy — see implementation plan §13.1, P04-20) |

---

## Verification gates (canonical list)

Normative numbering and acceptance criteria: **`phase-04-implementation-plan.md` §12.1** (**G-P04-01** through **G-P04-26**). **G-P04-08** (topology not in org-meaning payload) is defined in **`phase-04-topology-vs-meaning-doctrine.md`** and enforced by **`identity.boundary_checks`** (also listed on canonical verification gate list until org verification splits). Operator-console gates **G-P04-21–G-P04-26** are in **`phase-04-control-plane-doctrine.md` §18**. This index does not duplicate gate text — avoid drift.

---

## GO / NO-GO (runtime)

**P04-01:** normative index + anti-goals + program freeze version — **complete**; Step **2+** runtime may proceed per stage boundaries.

Per **`phase-04-implementation-plan.md` §20** and **`phase-04-architecture-identity-linking-doctrine.md`** final section: **NO-GO** to **full** Phase 04 linkage runtime (merge engine, ledger, replay jobs, etc.) until merge/hint/candidate/authoritative classes are frozen and cross-bundle equivalence is specified — **in addition to** P04-01. **Topology ≠ meaning:** **G-P04-08** enforced for org-meaning **payload** validation (P04-02); persistence-level org link table checks follow later steps.

---

## Upstream / downstream

- **Upstream:** Phase 01–03, Phase 3.5 `phase-35-organizational-continuity-foundation.md`, `vector.domains.cortex.continuity`.
- **Downstream:** Phase 05 consumes **`OrgGraphProjectionV1`** (export contract in implementation plan §18) — **no** graph traversal engine in Phase 04.
