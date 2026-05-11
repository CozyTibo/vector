# Phase 04 — Verification gates (normative registry + runner extension) (P04-15)

**Status:** normative **Phase 04 gate inventory** (`phase-04-implementation-plan.md` §12.1) + **org-scoped persisted verification slice** distinct from Phase **03** `cortex_canonical_verification_runs`.  
**Role:** freeze **policy gate IDs** for operator / CI contracts while the **canonical runner** remains the single execution engine for Phase **03+04** invariants.

---

## 1) Normative numbered gate slots (**G-P04-01** … **G-P04-26**)

Per **`phase-04-implementation-plan.md` §12.1** — these **26** ids are the **policy slots** (authorization, privacy, economics, operator console completeness, etc.).  
**Implementation note:** the live runner also emits **extension slugs** (e.g. **G-P04-ORG-01**, **G-P04-LINK-01**, **G-P04-CAND-01**, **G-P04-MRG-01**, **G-P04-HINT-01**, **G-P04-TMP-01**, **G-P04-BNDL-01**, **G-P04-RPL-01**, **G-P04-RULE-01**, **G-P04-PRIM-01**, **G-P04-EXP-01**, **G-P04-AMB-01**, **G-P04-VER-01**) — all remain **`G-P04-*`** and appear in the **Phase 04 slice** export below.

**Deferred (not yet hard-fail gates in runner):** slots whose behavior ships in later steps (**G-P04-07**, **G-P04-15**–**G-P04-11** numeric slot overlaps are partially covered by extension gates — see tracker Step **16–22**); **G-P04-18** / **G-P04-21** ship with **P04-17** (identity control-plane aggregate); **G-P04-22**–**G-P04-26** ship with **P04-18+** operator console surfaces.

---

## 2) Org identity verification slice (`identity.verification`)

| Artifact | Meaning |
| -------- | ------- |
| **`run_org_identity_verification`** | Invokes **`run_canonical_verification`** (Phase 03+04 combined engine), then **filters** `gates` to **`id` prefix `G-P04-`**, recomputes **PASS** over **hard_fail** only in that slice. |
| **`cortex_org_verification_runs`** | Optional **append-only** ledger of **Phase 04 slice** results for tenant-scoped audits (not a second runner). |
| **G-P04-VER-01** | **Static catalog coherence** — normative **01–26** registry complete + ontology metadata lists Phase **04** gate ids including **VER-01** (wired in `canonical_verification_engine`). |

---

## 3) Admin

- `POST /admin/tenants/{tenant_id}/cortex/identity/verification/run` — body mirrors canonical (`persist`, `materialization_sample_limit`); persists **`cortex_org_verification_runs`** when `persist=true`.  
- `GET /admin/tenants/{tenant_id}/cortex/identity/verification/runs` — recent org verification rows.

Canonical routes **`.../cortex/canonical/verification/*`** remain **unchanged** (full gate suite + `cortex_canonical_verification_runs`).

---

## 4) Normative references

- `phase-04-implementation-plan.md` — §12.1 gate list, Stage **P04-15**.  
- `phase-03-verification-engine-doctrine.md` — Phase **03** runner spine.  
- `vector.domains.cortex.identity.verification`, `vector.domains.cortex.canonical.canonical_verification_engine`.
