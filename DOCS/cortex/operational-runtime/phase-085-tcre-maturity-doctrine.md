# Phase 08.5 — TCRE reconstruction maturity

**Status:** normative.  
**Implements:** Steps 18–20 · **G-P085-TCRE-01..03**.

---

## Saturation scheduler (**G-P085-TCRE-01**)

**Goal:** drive `reconstruction_not_yet_run → 0` for tenants with canonical materializations.

**Law:**

- After phase 06 enqueue OR watchdog, schedule TCRE jobs until `reconstructed / mat_total ≥ θ_tcre` (default 0.85)
- Bounded jobs per hour per tenant (`CORTEX_TCRE_SATURATION_JOBS_PER_HOUR`)
- Pipeline-scoped jobs MUST include `substrate_pipeline_run_id`

---

## Reconstruction density (**G-P085-TCRE-02**)

| Metric | Definition |
| ------ | ---------- |
| `tcre_materialization_total` | canonical mats |
| `tcre_reconstructed_count` | from completed job summaries |
| `tcre_pending_count` | mat - reconstructed |
| `tcre_saturation_percent` | reconstructed / mat |
| `tcre_density_score` | 0–100 |

**Maturity:**

| Class | Saturation |
| ----- | ---------- |
| **R0** | no completed jobs |
| **R1** | < 25% |
| **R2** | 25–85% |
| **R3** | ≥ 85% |

---

## Omission explainability (**G-P085-TCRE-03**)

Surface per job / tenant:

- `chronology_degraded_count`
- `causal_legality_unverified`
- `reconstruction_coverage_gap`
- upstream omissions: `unmaterialized_raw`, `traversal_never_executed`

**Completeness fix:** TCRE stage MUST be `degraded` when `reconstruction_not_yet_run > 0` AND `mat_total > 0` (remove healthy-on-never-run).
