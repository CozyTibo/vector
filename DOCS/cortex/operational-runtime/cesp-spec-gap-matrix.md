# CESP spec gap matrix (Phase 08.5)

**Status:** living document.  
**Discipline:** P0 blocks Step 36 freeze; P1 blocks **Frozen (runtime)** for that slice.

---

## Active P0

| Id | Step | Gap | Owner slice |
| -- | ---- | --- | ----------- |
| P0-085-01 | 6 | Post-ingestion refresh does not guarantee Celery workers running — document + health gate | scheduling |
| P0-085-02 | 2 | ~~Graph completeness still shows **healthy** with 100% orphans~~ — **Closed** Step 2 + Step 13 (`propagate_graph_completeness_stage_v1`) | completeness |
| P0-085-03 | 2 | ~~TCRE shows **healthy** on `reconstruction_not_yet_run`~~ — **Closed** Step 2 | completeness |
| P0-085-04 | 2 | ~~Retrieval **healthy** when eligible=0 but upstream TCRE pending~~ — **Closed** Step 2 | completeness |
| P0-085-05 | 2 | Synthesis **starved vs idle** classification in ledger metrics — **Partial** (Step 2 law; **G-P085-SYN-02** automation Step 25) | synthesis |
| P0-085-06 | 11 | ~~No `schedule_graph_density_pass_v1` — promotion not automated~~ — **Closed** Step 11 | graph |
| P0-085-07 | 14 | ~~No automatic traversal scheduler after phase 05~~ — **Closed** Step 14 | traversal |
| P0-085-08 | 18 | ~~No TCRE saturation scheduler~~ — **Closed** Step 18 | tcre |
| P0-085-09 | 31 | ~~Admin cockpit + explorer APIs not built~~ — **Closed** Steps 30–31 (**G-P085-CP-01**, **G-P085-CP-02**) | admin |
| P0-085-10 | 36 | ~~**CESP-CERT-PACK-1** + `verify_cesp_cert_pack_v1` not implemented~~ — **Closed** Step 36 | certification |

---

## Active P1

| Id | Step | Gap |
| -- | ---- | --- |
| P1-085-01 | 7 | Dead-letter table not durable (only continuation detail_json) |
| P1-085-02 | 21 | `eligible_scope_growth_rate` not in rollup DB |
| P1-085-03 | 21 | Retrieval metrics in-process only — need prometheus/rollup |
| P1-085-04 | 27 | Multi-dimensional maturity not implemented (coarse STAGE_0–6 only) |
| P1-085-05 | 32 | ~~Pipeline progression timeline UI~~ — **Closed** Step 32 (**G-P085-CP-03**) |
| P1-085-06 | 33 | ~~Queue backpressure not wired to post-ingestion debounce~~ — **Closed** Step 33 (**G-P085-ECON-01**) |
| P1-085-07 | 16 | ~~Stalled traversal recovery~~ — **Closed** Step 16 |
| P1-085-08 | 9 | Missing continuation for TRAVERSAL_COMPLETION wait kind |

---

## Partially shipped (code exists)

| Step | Artifact |
| ---- | -------- |
| 5–9 | `pipeline_continuation.py`, `stalled_pipeline_recovery.py`, migration 0082, watchdog task |
| 21 | `retrieval_materialization_diagnostics.py`, `retrieval_skip_registry.py` |
| 24–25 | `synthesis_eligibility_explainability.py`, `synthesis_activation_audit.py` |
| 27–28 | `substrate_runtime_maturity.py`, `substrate_operational_health.py` (coarse) |
| 30 | Partial admin routes on substrate-pipeline + synthesis |

---

## Closed / N/A

| Id | Resolution |
| -- | ---------- |
| — | Phase 08 SIL freeze remains authoritative for synthesis law |

---

## Promotion rules

1. Implement + test → move to **Closed** with PR link.  
2. Doctrine-only gap → update doctrine in same PR.  
3. New gap from red-team → add row before merge.
