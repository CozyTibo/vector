# Phase 08.5 — Implementation sequencing plan

**Status:** normative.  
**Order:** waves align with FF-P085-0..6.

---

## Wave 0 — Program lock (Steps 1–4)

- [x] Normative index + executive brief  
- [x] Gap matrix baselined (`cesp_gap_matrix` + **G-P085-GAP-MATRIX**)  
- [x] `vector.domains.cortex.operational_runtime.normative` (`PHASE085_PROGRAM_FREEZE_VERSION`)

**Exit:** doctrine review sign-off.

---

## Wave 1 — Continuity hardening (Steps 5–9) **Partial**

- [x] Migration 0082 + continuation model  
- [x] Phase 06 wait + TCRE resume + idempotent receipt  
- [x] Watchdog task + beat  
- [ ] DLQ table + recovery receipts durable  
- [ ] Integration test: mock ingest → phase 07 without manual action  
- [x] `G-P085-CONT-01` pytest (`test_phase085_pipeline_continuation.py`)
- [ ] `G-P085-WATCH-01` pytest

**Exit:** 95% pipeline 07 enqueue after TCRE in test harness.

---

## Wave 2 — Fake-green elimination (completeness) **P0** (Step 2 shipped)

- [x] `graph_completeness_projection` — degraded on orphans blocking  
- [x] `tcre_completeness_projection` — degraded on `reconstruction_not_yet_run`  
- [x] `retrieval_completeness_projection` — starvation class  
- [x] `synthesis_completeness_projection` — starved vs idle  
- [x] `G-P085-ANTI-IDLE-01` CI (`test_phase085_fake_green_completeness.py`)

**Exit:** local mock tenant shows **degraded/starved** not green on 0 retrieval.

---

## Wave 3 — Density schedulers (Steps 10–20)

- [ ] Graph promotion pass + metrics  
- [ ] Traversal auto-scheduler + pending explorer backend  
- [ ] TCRE saturation scheduler  
- [ ] Extend phase 07 materialization (org links shipped) + report always

**Exit:** golden tenant `tcre_saturation ≥ 85%`, `indexed_count > 0`.

---

## Wave 4 — Synthesis activation (Steps 24–26)

- [x] Activation audit persistence  
- [x] Eligibility explain APIs  
- [ ] Wire phase 08 auto-run when eligible > 0 post-07  
- [ ] Throughput rollup table (daily)

**Exit:** `completed_synthesis_jobs > 0` on golden tenant.

---

## Wave 5 — Maturity + health (Steps 27–29)

- [ ] Multi-dimensional maturity evaluator  
- [ ] Durable metrics rollup (replace in-process-only for admin)  
- [ ] Autonomous recovery score

**Exit:** `OPERATIONAL_ALIVE` computable in admin.

---

## Wave 6 — Admin cockpit (Steps 30–32)

- [ ] Operational command center page  
- [ ] Timeline + heatmap + explorers (frontend)  
- [ ] Overview card integration (classification badges)

**Exit:** operator can diagnose mock tenant starvation in < 2 min without SQL.

---

## Wave 7 — Economics + certification (Steps 33–36)

- [ ] Caps in settings + enforcement  
- [ ] Replay storm circuit breaker  
- [ ] `CESP-CERT-PACK-1` generator  
- [ ] 7d soak + **G-P085-CLOSE-01**

**Exit:** Phase 09 authorized.

---

## Dependency graph

```
Wave 0 → Wave 1 → Wave 2
              ↓
         Wave 3 → Wave 4 → Wave 5 → Wave 6 → Wave 7
```

Wave 2 SHOULD land early (fixes misleading UI during rest).
