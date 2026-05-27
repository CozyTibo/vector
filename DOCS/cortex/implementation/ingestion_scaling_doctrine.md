# Ingestion scaling doctrine

**Status:** normative — complements [minimal_ingestion_doctrine.md](./minimal_ingestion_doctrine.md)  
**Audience:** anyone operating or extending Cortex ingestion

---

## Principle

Scale the **current loop**, not a new platform:

```text
1 Beat leader → scheduler_tick → enqueue run_sync →
  load_checkpoint → fetch_page → append_raw → update_checkpoint → stop_on_budget
```

---

## What we scale

| Lever | How |
|-------|-----|
| Throughput | More **stateless** `cortex_live` workers (manual +1 task before autoscaling) |
| Depth | **Time budgets**, **ring indices**, honest **cursors** |
| Politeness | **`min_gap`** per tenant×connector; skip enqueue if **run already running** |
| Truth | Postgres: ticks, runs, checkpoints, raw counts |

---

## Queue topology (ceiling)

| Queue | Work |
|-------|------|
| `vector` | Beat `scheduler_tick`, email, misc |
| `cortex_live` | `run_sync` |
| `cortex_replay` | `run_sync_replay` |

**One Beat process** (dedicated ECS task or single known container). No Beat on horizontally scaled API replicas.

---

## What we refuse

- Per-tenant / per-connector queues  
- DAG / planner / debt engine  
- Queue-depth “smart skip” (use operator pause instead)  
- Distributed locks as default (fix duplicate Beat in deploy)  
- Autoscaling projects before sustained backlog pain  

---

## Operator health (not `run.status` alone)

- Raw row counts + `fetched_at` span per `resource_type`  
- Checkpoint `backfill_complete`, `introduced_at`, `meta.exhaust_depth`  
- Beat history: **queued** = enqueued, no run yet; **running** / **completed** from `ingestion_runs`

---

## Defaults (prod guidance)

- `CORTEX_INGESTION_SCHEDULER_INTERVAL_SECONDS=120`  
- `CORTEX_INGESTION_MIN_GAP_SECONDS=300` (≥ typical incremental duration)  
- Ingestion worker: `cortex_live,cortex_replay`, concurrency 2, prefetch 1  
