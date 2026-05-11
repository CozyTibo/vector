# Phase 04 — Closure gates & org certification pack (P04-22)

**Status:** normative for Step **22** (Phase 04 operator closure + certification archive).  
**Purpose:** mirror the Phase **03** Step **18** pattern for **organizational continuity**: a deterministic **certification pack JSON**, a small **closure gate matrix**, and optional **persisted archives** — without conflating Phase 03 canonical closure rows (**G-P03-14–G-P03-21**) with Phase 04.

## 1) Scope

- **In scope:** org-scoped certification evidence (`identity_control_plane_v1` excerpt, readiness economics excerpt, Phase 04 gate slice, last org verification run pointer), **canonical verification** full-tenant excerpt (all gates), and **G-P04-CLOSE-01** as the single **new** canonical-verification **hard_fail** gate that certifies the pack contract + pre-rows.
- **Out of scope:** Phase 05 graph traversal, new merge policy semantics, redefinition of **G-P04-01–G-P04-26** acceptance text (those remain in `phase-04-verification-gates-doctrine.md` and `phase-04-implementation-plan.md` §12.1).

## 2) Artifacts

| Artifact | Location |
| -------- | -------- |
| Pack builder + contract | `vector.domains.cortex.identity.org_identity_certification_pack` |
| Persisted archives | Postgres **`cortex_org_certification_archives`** |
| Admin (read + archive) | `GET/POST .../cortex/identity/certification-pack` family (see ontology pointer metadata) |
| Engine gate | **`G-P04-CLOSE-01`** in `run_canonical_verification` |

## 3) Closure gate matrix (org pack)

Rows are **operator-audited** slices; only **`severity: hard_fail`** rows block **POST …/archive**.

| Row id | Meaning |
| ------ | ------- |
| **G-P04-CLOSE-MAP-01** | Full `run_canonical_verification` result: every **`hard_fail`** gate must **`passed: true`**. |
| **G-P04-CLOSE-MAP-02** | Phase 04 slug slice (`G-P04-*` gates only): every **`hard_fail`** among those gates must **`passed: true`**. |
| **G-P04-CLOSE-01** | Structural **`verify_phase04_org_identity_certification_pack_contract`** OK **and** MAP-01/MAP-02 both passed (certification proof artifacts). |

## 4) Archive semantics

- **POST** persists **only** when **all hard-fail** closure rows pass (including **G-P04-CLOSE-01**).
- Archives are **append-only** audit rows (`pack_json` is immutable after insert).
- Operators should run **`POST .../cortex/identity/verification/run`** (org slice) and canonical verification as needed **before** archiving; the pack captures excerpts at **`built_at_clock`**, not live subscription.

## 5) Relation to Phase 03

- Phase **03** certification routes remain under **`/cortex/canonical/certification-pack`**.
- Phase **04** certification routes are under **`/cortex/identity/certification-pack`** — parallel pack, **not** a merge into the canonical archive table.
