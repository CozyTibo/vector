# Cortex substrate queue runbook (Wave 0)

**Scope:** INGEST → MATERIALIZE → IDENTITY → GRAPH only.  
**Authoritative motion:** `mark_dirty_and_enqueue_convergence_v1` → `vector.cortex.execution.run_slice`.

---

## Queue ownership

| Queue | Worker role | Tasks | Owns |
|-------|-------------|-------|------|
| `cortex_live` | ingestion | `vector.cortex.ingestion.run_sync` | Live connector pull → raw rows |
| `cortex_replay` | ingestion | `vector.cortex.ingestion.run_sync_replay` | Isolated replay raw (no auto dirty) |
| `vector` | substrate | `vector.cortex.execution.run_slice`, `vector.cortex.convergence.sweep` | Convergence slices (canonical + identity + graph export) |

**Beat (usually on `vector`):** `vector.cortex.ingestion.scheduler_tick`, `vector.cortex.convergence.sweep`.

**ECS:** Split ingestion and substrate workers in production (`worker_queue_roles_v1.py`). Local docker-compose often runs all queues on one worker — that masks prod starvation.

---

## Authoritative path

```
run_sync [cortex_live]
  → RawIngestionRecord
  → mark_dirty_and_enqueue_convergence_v1
  → run_execution_slice_task [vector]
  → run_dual_lane_convergence_v1
       Lane A: drain_forward_progress_backlog → materialize → anchor
       Lane B: run_identity_substrate_repair_slice_v1 → promote (inline) → graph export
```

| Step | Owner function |
|------|----------------|
| Dirty | `convergence_dispatch.mark_dirty_and_enqueue_convergence_v1` |
| Materialize + anchor | `materialize_raw_record` + `upsert_identity_anchor_for_materialization` |
| Identity repair | `identity_substrate_repair_v1.run_identity_substrate_repair_slice_v1` |
| Promotion | `graph_density_promotion.run_graph_density_promotion_pass_v1` (end of repair slice only) |
| Graph export | `projection_export.run_graph_projection_export_for_pipeline_v1` |

**Wave 1 (no duplicate promotion):** Pre-slice `schedule_graph_density_promotion_on_convergence_worker_v1`, event-trigger promotion, and orphan-stitch auto-promotion are removed. Promotion runs at most once per repair slice when backfill/regen produced work.

**Phase status (Wave 1):** `phase_run.status` follows receipt — `BLOCKED`/`topology_wait` → `waiting`; phase 03 `FAILED` → `failed`; repair-in-progress → `waiting` (not green `completed`).

---

## Operator repair (Wave 2)

| Action | API | Behavior |
|--------|-----|----------|
| **Rebuild identities** | `POST .../cortex/operator/actions` `{ "action": "rebuild_identities", "confirmation": "REBUILD IDENTITIES FROM CANONICAL ANCHORS" }` | `reset_identity_substrate_repair_state_v1` + `mark_dirty_and_enqueue_convergence_v1` — **no** `identity_rebuild_from_anchors` replay job |

**Wave 3 (removed dead paths):**

- Celery tasks `vector.cortex.identity.regenerate_link_candidates` and `replay_authoritative_links` are **not registered** (use convergence + repair slice).
- Orphan stitch does **not** auto-schedule promotion.
- Post-ingest debounce settings removed — handoff is immediate `mark_dirty_and_enqueue_convergence_v1`.

Debug-only (add `?debug=1` on operator pages for panel, or call API directly):

- `POST .../cortex/debug/identity/backfill/from-canonical-anchors`
- `GET/POST .../cortex/debug/identity/replay-jobs`
- `POST .../cortex/debug/identity/full-substrate-refresh?debug_acknowledged=true&bundle_id=...`

---

## Operator truth (Wave 0)

- **API:** `GET /admin/tenants/{tenant_id}/cortex/substrate/truth`
- **Embedded in:** `GET /admin/tenants/{tenant_id}/cortex/operator/overview` → `substrate_truth`
- **Snapshot script:** `python backend/scripts/substrate_truth_audit_snapshot.py --tenant <uuid> --json`

Trust **`overall_status`** and **`red_rules`**, not pipeline `completed` or raw `edge_count`.

---

## Runtime flags (must be on in prod)

| Setting | Effect if false |
|---------|-----------------|
| `cortex_post_ingestion_substrate_refresh_enabled` | Live ingest does not enqueue convergence |
| `cortex_execution_event_triggers_enabled` | Post-ingest handoff does not mark dirty |

---

## Common failures

| Symptom | Check |
|---------|--------|
| Raw grows, nothing else | `vector` worker consuming? |
| Dirty forever | Slice errors on lease `last_error` |
| Replay “fixed” nothing | Replay does not mark dirty — use live sync or manual dirty |
| Graph edges climb, people don’t merge | Read `substrate_truth.graph.isolated_pct` and `promotion_rule_count` |

---

## Deploy check (minimal)

1. `probe_prod_ecs_deploy_v1` — API and worker SHA match.
2. `substrate_truth_audit_snapshot.py` — diff vs `DOCS/audits/baselines/substrate_truth_fizzer_wave0_baseline.json`.
