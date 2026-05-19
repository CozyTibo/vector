# Phase 08.5 — Runtime economics & scale

**Status:** normative.  
**Implements:** Steps 33–34 · **G-P085-ECON-01**, **G-P085-ECON-02**.

---

## Queue pressure governance (**G-P085-ECON-01**)

| Knob | Default | Purpose |
| ---- | ------- | ------- |
| `CORTEX_SUBSTRATE_PIPELINE_MAX_CONCURRENT_PER_TENANT` | 1 | no overlapping runs |
| `CORTEX_TCRE_SATURATION_JOBS_PER_HOUR` | 120 | cap reconstruction storm |
| `CORTEX_TRAVERSAL_MAX_WALKS_PER_PASS` | 32 | fanout limit |
| `CORTEX_SYNTHESIS_PIPELINE_MAX_SCOPES` | 32 | per pass |
| `CORTEX_GRAPH_PROMOTION_MAX_PER_PASS` | 200 | link promotion |

**Backpressure:** when `vector` queue depth > `θ_queue`, defer post-ingestion refresh countdown.

---

## Density caps

Saturation schedulers MUST degrade gracefully:

- emit `SD-UPSTREAM-CAP` / operational omission — not silent drop
- never exceed per-tenant hourly job budget

---

## Replay storms (**G-P085-ECON-02**)

Detect: `replay_divergence_rate` spike across retrieval + synthesis.

Response:

1. pause exploration partition jobs
2. pin policy pack digest
3. require operator ack to resume saturation

---

## Bounded guarantees

| Guarantee | Bound |
| --------- | ----- |
| Recovery attempts per pipeline run | ≤ 5 |
| Duplicate phase 07 enqueues per receipt | 0 |
| Max index epochs created per pipeline run | 1 (idempotent materialization) |
