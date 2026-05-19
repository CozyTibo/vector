# Phase 08.5 — Phase 09 readiness doctrine

**Status:** normative.  
**Implements:** Step 35 · **G-P085-READY-01**.

---

## Hard gate

**Phase 09 implementation MUST NOT begin** until **G-P085-CLOSE-01** passes on `main` and certification pack archived.

---

## Readiness checklist (all required)

| # | Criterion | Verification |
| - | --------- | ------------ |
| R1 | Continuation law wired 06→07→08 | integration test + 95% completion rate in soak |
| R2 | Watchdog + auto-recover shipped | `G-P085-WATCH-01` |
| R3 | Fake-green idle eliminated | `G-P085-ANTI-IDLE-01` on completeness projections |
| R4 | Retrieval materialization reports on every phase 07 | DB constraint / test |
| R5 | `explain_synthesis_eligibility_v1` in admin | e2e admin test |
| R6 | Graph density pass OR documented defer with P0 cleared | gap matrix |
| R7 | Traversal scheduler OR starvation visible | gap matrix |
| R8 | TCRE saturation scheduler | `tcre_saturation ≥ θ` in golden tenant |
| R9 | Synthesis activation audits | non-zero jobs in golden tenant |
| R10 | Multi-dimensional maturity | `OPERATIONAL_ALIVE` on golden tenant |
| R11 | Admin cockpit surfaces 1–16 | UX checklist |
| R12 | Economics caps configured in prod | settings audit |
| R13 | No Active P0 in `cesp-spec-gap-matrix.md` | review |
| R14 | Phase 08 freeze still valid | no SYN schema drift |
| R15 | 7-day soak report | ops sign-off |

---

## Golden tenant profile

**Tenant:** mock dataset with cortex capability scenarios (blocked release, graph connectivity).

**Must demonstrate within 2h of connect + ingest:**

1. Non-zero published retrieval rows  
2. Non-zero eligible scopes  
3. ≥ 1 completed synthesis job (stub LLM acceptable)  
4. Zero unrecovered stalls  

---

## Handoff to Phase 09

Phase 09 may assume:

- `SynthesisIntelligenceArtifactV1` arrives on schedule for active tenants
- `synthesis_publication_epoch` advances with retrieval epoch
- Operator cockpit explains starvation within 1 click

Phase 09 MUST NOT implement substrate recovery (remains 08.5).
