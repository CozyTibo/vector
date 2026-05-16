# Phase 07 — Retrieval completeness doctrine

**Status:** normative.

---

## Stage definition (substrate pipeline)

**Stage id:** `retrieval`  
**Label:** Retrieval  
**Position:** After `tcre`, before Phase 08 consumption.

---

## Eligible object count

`eligible_artifacts` = count of indexable addresses:

- TCRE chronology receipts + causal edges for tenant (completed jobs)  
- OCTS completed walks (durable store)  
- Authoritative org links + entities (when graph-scoped queries enabled)  
- Canonical materializations (when mat-scoped queries enabled)  

**RULE RET‑COMP‑01:** Eligible ≠ raw row count.

---

## Processed count

`indexed_entries` = rows in `cortex_retrieval_index_entries` with `index_epoch` = current published epoch.

---

## States

| Condition | `substrate_state` |
| --------- | ----------------- |
| `eligible = 0` | `healthy` (idle) |
| `eligible > 0` AND `indexed = 0` | `degraded` + `retrieval_index_never_built: 1` |
| `indexed / eligible < threshold` | `degraded` |
| `replay_conflicted` upstream | `degraded` + `replay_posture: unsafe` |
| `indexed / eligible ≥ threshold` AND replay-safe queries | `healthy` |

---

## Metrics exposed on stage envelope

| Metric | Meaning |
| ------ | ------- |
| `eligible_artifact_count` | Denominator |
| `indexed_count` | Numerator |
| `retrieval_coverage_percent` | pct(indexed, eligible) |
| `replay_safe_query_percent` | recent queries |
| `walk_record_count` | OCTS walks (context) |
| `retrieval_never_indexed` | bool |

---

## `intentionally_excluded_count`

When `eligible > 0` but index job pending: show pending index build count (mirror traversal pending walks UX).

---

## Omission classes on stage

| Class | When |
| ----- | ---- |
| `retrieval_index_never_built` | No publish epoch |
| `retrieval_index_stale` | Lag > policy |
| `retrieval_upstream_tcre_gap` | TCRE gap > 0 |
| `retrieval_replay_divergence` | Recent twin fail |

---

## Global rollup impact

`derive_substrate_state_from_stages` MUST treat retrieval `degraded` like other stages (>5% degraded or unresolved rules).
