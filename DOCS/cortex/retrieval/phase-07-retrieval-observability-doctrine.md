# Phase 07 — Retrieval observability doctrine

**Status:** normative.

---

## Metrics (tenant-scoped, integers / millis only in control plane)

| Metric | Type | Meaning |
| ------ | ---- | ------- |
| `retrieval_queries_total` | counter | Executed queries |
| `retrieval_queries_by_legality` | map | Count per legality class |
| `retrieval_omissions_total` | counter | Omission rows emitted |
| `retrieval_omissions_by_class` | map | `RD-*` histogram |
| `retrieval_latency_ms_p50/p95` | gauge | Wall time |
| `retrieval_replay_divergence_total` | counter | G-P07-REPLAY-01 failures |
| `retrieval_legality_failures_total` | counter | Pre-execution rejects |
| `retrieval_index_lag_epochs` | gauge | Published vs head |
| `retrieval_provenance_coverage_percent` | int 0-100 | Hits with full digest set |
| `retrieval_completeness_percent` | int | Indexed / eligible |

---

## Execution logs (structured)

Each query MUST log:

- `retrieval_query_replay_identity`  
- `workload_class`, `intent`, `execution_partition`  
- `retrieval_legality_class`  
- `hit_count`, `omission_count`  
- `duration_ms`  
- `engine_build_ref` (retrieval runtime)  
- `policy_digest`  

**No raw hit payloads in info logs** — only digests and counts.

---

## Health model (`build_retrieval_runtime_health_v1`)

| Field | Source |
| ----- | ------ |
| `substrate_state` | completeness projection |
| `replay_posture` | aggregate of recent queries |
| `last_replay_divergence_at` | twin failures |
| `index_epoch` | index publish |
| `degraded_percent` | recent query rollup |

---

## Alerts (operator-facing thresholds — policy pack)

| Alert | Condition |
| ----- | --------- |
| Retrieval critical | completeness < 50% with TCRE jobs present |
| Replay divergence spike | >3 divergences / 1h |
| Index stale | `index_lag_epochs` > policy max |
| Legality failure burst | `retrieval_forbidden` rate > 1% |

---

## Audit trail

Persist `cortex_retrieval_query_audit` (table spec in runtime architecture):

- receipt digest  
- operator_user_id (when admin)  
- query envelope hash  
- result legality  

Retention: align Phase 02 raw memory policy (configurable).
