# Phase 08.5 — Operational health & maturity doctrine

**Status:** normative.  
**Implements:** Steps 27–29 · **G-P085-MAT-01**, **G-P085-HEALTH-01**, **G-P085-HEALTH-02**.

---

## Multi-dimensional maturity (replaces coarse STAGE_0–6 only for certification)

| Dimension | Score 0–100 | Weight |
| --------- | ----------- | ------ |
| **continuity** | pipeline 07–08 completion, stall rate | 25% |
| **graph_density** | connectivity_ratio | 15% |
| **traversal_completion** | walk completion rate | 15% |
| **tcre_saturation** | reconstruction % | 15% |
| **retrieval_density** | acceptance rate | 20% |
| **synthesis_activation** | scope coverage | 10% |

**Composite:** `operational_confidence_score` = weighted sum.

---

## Maturity classes

| Class | Requirements |
| ----- | ------------ |
| **STRUCTURAL_ONLY** | Phases 01–08 legal; no aliveness |
| **PROGRESSING** | continuity score ≥ 40 |
| **DENSITY_EMERGING** | retrieval_density ≥ 40 AND tcre ≥ R2 |
| **OPERATIONAL_ALIVE** | all dimension ≥ 60, composite ≥ 70, no active starvation |
| **PRODUCTION_READY** | OPERATIONAL_ALIVE + 7d soak + G-P085-CLOSE-01 |

---

## Health dimensions (**G-P085-HEALTH-01**)

| Dimension | healthy | degraded | critical |
| --------- | ------- | -------- | -------- |
| substrate_continuity_health | no stall | waiting < T_stall | stalled |
| retrieval_density_health | indexed > 0 | empty publish | starvation |
| async_resume_health | resumes ok | duplicate stalls | missing continuation |
| synthesis_activation_health | scopes running | eligible no jobs | forbidden spike |
| orchestration_progress_health | past TCRE | stuck at 06 | pipeline failed |

---

## Autonomous recovery score (**G-P085-HEALTH-02**)

```
recovery_score = recovered_watchdog / (recovered + failed_dlq)
```

Target ≥ **0.9** rolling 7d.

---

## Definitions

| Term | Definition |
| ---- | ---------- |
| **Alive** | OPERATIONAL_ALIVE class |
| **Stable** | no stall events 24h + recovery_score ≥ 0.9 |
| **Production-ready** | PRODUCTION_READY class + Phase 09 readiness pass |
