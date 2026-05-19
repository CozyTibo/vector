# Phase 08.5 — Retrieval density doctrine

**Status:** normative.  
**Implements:** Steps 21–23 · **G-P085-RET-01**, **G-P085-RET-02**.

---

## Core law (**G-P085-RET-01**)

**Retrieval density** = `indexed_rows_in_published_epoch / eligible_indexable_addresses`.

**Materialization report** (`cortex_retrieval_materialization_reports`) REQUIRED on every `materialize_retrieval_index_for_pipeline_v1`.

**Skip taxonomy:** `RET-SKIP-*` (canonical); every skip MUST include `upstream_code`, `ret_skip_code`, `replay_safe`, dependency trace.

---

## Starvation gates (**G-P085-RET-02**)

| Condition | Classification |
| --------- | -------------- |
| `tcre_completed > 0` AND `indexed = 0` | **operational_starvation** |
| `walks_completed > 0` AND `indexed = 0` | **operational_starvation** |
| `eligible = 0` AND no upstream | **healthy_idle** |
| published epoch empty | `retrieval_index_empty` omission |

**Index freshness:** `index_age_seconds = now - published_at`; degrade if > `T_index_stale`.

---

## Metrics (durable + ephemeral)

| Metric | Storage |
| ------ | ------- |
| `retrieval_rows_materialized_total` | prometheus / rollup table |
| `retrieval_row_acceptance_rate` | tenant rollup |
| `retrieval_epoch_empty_rate` | global |
| `eligible_scope_growth_rate` | delta eligible / hour |

**Rule:** overview card `total_objects` for retrieval = `eligible_artifact_count`, `processed_count` = `indexed_count` — never hide zero eligible as healthy when starved.

---

## Completeness propagation (Step 23)

Update `project_retrieval_completeness_v1`:

- Add `operational_starvation` flag to metrics
- `substrate_state = degraded` on starvation
- Link to latest materialization report id in `detail_route` query param
