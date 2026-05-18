# Phase 08 — Spec gap matrix

**Status:** living document for P0/P1 promotion discipline.  
**Doctrine freeze:** **`Frozen (implementation)`** — **P08-FINAL-FREEZE-2026-05-17** (Steps **1–35**).  
**Last doctrine pass:** 2026-05-17 (Step **35** sign-off).

---

## Active gaps

| ID | Step | Severity | Gap | Resolution |
| -- | ---- | -------- | --- | ---------- |
| — | — | — | **No Active P0** after initial doctrine pass | — |

---

## Active P1 (non-blocking)

| ID | Step | Gap | Target |
| -- | ---- | --- | ------ |
| P08-P1-01 | 11 | Live LLM vendor adapter not specified per provider | Add adapter annex when vendor chosen |
| P08-P1-02 | 12 | Prompt templates live only as policy refs | Ship `synthesis/templates/` at Step 12 impl |
| P08-P1-03 | 23 | SPA wireframes not included | UX pass parallel to Step 23 |
| P08-P1-04 | 33 | Retention / GDPR deletion policy | Align with Phase **02** retention |

---

## Closed / N/A

| ID | Note |
| -- | ---- |
| P08-P0-ARCH | Architecture doctrine complete in `phase-08-synthesis-runtime-architecture.md` |
| P08-P0-E2E | E2E flow defined in runtime-flow + e2e-operational docs |
| P08-P0-PIPE | Pipeline integration specified in `phase-08-pipeline-orchestration.md` |

---

## Promotion rules

- **P0:** blocks **Frozen (doctrine)** for affected step — MUST be empty before P08-FINAL-FREEZE  
- **P1:** may ship as **Strong (Caveats)** with matrix row  
- Implementation may not start a step with **Active P0** targeting that step  
