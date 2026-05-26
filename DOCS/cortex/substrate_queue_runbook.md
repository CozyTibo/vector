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

**Wave 4 (graph truth KPIs):**

- Phase 04 receipt primary signals: `projection_hash_changed`, `isolated_pct` / `isolated_pct_delta` (not `node_count` / `edge_count`).
- `CORTEX_SUBSTRATE_SKIP_WALK_SCHEDULE_V1=true` (default): hash persisted on lease, no OCTS walk schedule from phase 04.
- People operator UI lists **clusters** (`GET .../cortex/operator/people`) with `cluster_size` and `connector_id_count`.

**Wave 6 (residue purge):**

- Deleted `graph_hash_autonomous_chain` experiment and `CORTEX_GRAPH_HASH_AUTONOMOUS_CHAIN` setting.
- Removed `post_ingestion_refresh_celery_task_id` and fake `task_id` on `schedule_substrate_pipeline_v1`.
- Production ingest uses `sync_router.execute_connector_sync` (not `sync_executor` shim).
- Static gate: `verify_no_substrate_residue_v1` / `test_substrate_wave6_residue_purge.py`.
- Module map: [substrate_coherence_modules_v1.md](./substrate_coherence_modules_v1.md).

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

## Deploy check (Wave 5 — mandatory)

**CI (every PR):** GitHub Actions `backend-substrate-coherence` runs M9 + waves 1–5 static gates and substrate pytest.

**CD (every main deploy):**

```bash
# After ECS stable (automated in deploy.yml)
cd backend && PYTHONPATH=src python scripts/substrate_post_deploy_gate.py \
  --expected-sha "$GITHUB_SHA" \
  --baseline ../DOCS/audits/baselines/substrate_truth_fizzer_wave0_baseline.json
```

Requires `DB_PROD_*` secrets for baseline diff; ECS probe always runs.

**24h Fizzer soak (V6–V8):**

```bash
cd backend && PYTHONPATH=src python scripts/substrate_soak_v6_v8_check.py \
  --tenant c08ef32b-f89a-40f6-9566-e19b5329436f --json
# Optional: --isolation-waiver when signed ticket exists
# V7: pass --prior-graph-hash from earlier sample in the window
```

| Check | Script / gate |
|-------|----------------|
| ECS SHA | `substrate_post_deploy_gate.py` → `probe_prod_ecs_deploy_v1` |
| Regression diff | same script vs committed baseline |
| V6–V8 soak | `substrate_soak_v6_v8_check.py` |

Manual snapshot (update baseline after green deploy):

1. `substrate_truth_audit_snapshot.py` — diff vs `DOCS/audits/baselines/substrate_truth_fizzer_wave0_baseline.json`.
