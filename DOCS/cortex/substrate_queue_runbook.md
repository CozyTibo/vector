# Cortex substrate runbook (Waves 0–8)

**Scope:** INGEST → MATERIALIZE → IDENTITY → GRAPH.  
**Truth:** `GET /admin/tenants/{id}/cortex/substrate/truth` (`substrate_truth_v1`).  
**Motion:** `mark_dirty_and_enqueue_convergence_v1` → Celery `vector.cortex.execution.run_slice` → `run_dual_lane_convergence_v1`.

---

## Queues

| Queue | Tasks | Role |
|-------|-------|------|
| `cortex_live` | `run_sync`, `scheduler_tick` | Ingest raw |
| `cortex_replay` | `run_sync_replay` | Replay raw (no auto dirty) |
| `vector` | `run_slice`, `convergence.sweep` | Substrate slices |

Split ingestion vs substrate workers in ECS (`worker_queue_roles_v1.py`).

---

## Mutator registry (authoritative)

| ID | Owner | Trigger | Mutates | Observable |
|----|-------|---------|---------|------------|
| ingest | `execute_connector_sync` | ingest | raw rows, checkpoints | `ingest_handoff_v1` after sync |
| dirty | `mark_dirty_and_enqueue_convergence_v1` | ingest, operator_reset | convergence lease | `obligation_epoch`, dirty flag |
| materialize | `drain_forward_progress_backlog` | slice | anchors, materializations | `canonical` lane outcome |
| repair | `run_identity_substrate_repair_slice_v1` | slice | entities, candidates, repair cursor | `identity.repair`, slice receipt |
| promote | `run_graph_density_promotion_pass_v1` | slice | **`cortex_org_links`** | `graph_substrate.promotion_rule_count` |
| export | `run_graph_projection_export_for_pipeline_v1` | slice | graph hash / phase receipt | `graph_substrate.isolated_pct` |
| revoke_link | `soft_revoke_org_link` | operator API | link `revoked_at` | link explorer counts |
| operator_reset | `operator_rebuild_identities_v1` | operator_reset | repair cursor + dirty | truth `motion` + repair |
| sweep | `run_convergence_sweep_v1` | beat safety net | enqueue only | sweep metrics |

**Org links:** only `run_graph_density_promotion_pass_v1` (via `promote_candidate_to_authoritative_link`) and explicit `soft_revoke_org_link`. No background replay job may rebuild substrate.

---

## Predict next mutation (lease → hint)

Read `substrate_truth_v1.operational.next_mutation_hint` (also `next_retry_at`, `canonical_topology_gate`, `dual_lane.execution_lane_ran_despite_canonical_stall`).

| Lease signal | Next mutation |
|--------------|----------------|
| `STALLED` | Fix `last_error`; operator Repair or clear stall |
| `DIRTY` | Worker runs dual-lane slice (canonical then execution) |
| Canonical `topology_wait` + not may_proceed | Drain deferrals / materialize |
| `topology_wait` + may_proceed (R1 on) | Execution lane repair/promote on slice |
| `WAITING` + TCRE | Resume at phase 07 when job completes |

---

## Operator actions

| Action | API |
|--------|-----|
| View substrate | `GET .../cortex/substrate/truth` |
| Repair | `POST .../cortex/operator/actions` `rebuild_identities` + confirmation |
| Ingest | Connector `trigger-sync` (dirty only via sync complete — not admin-only dirty) |
| Debug replay | `.../cortex/debug/identity/replay-jobs` (primary routes **410**) |

---

## Collapsed hidden behaviors

- No duplicate promotion (pre-slice, event trigger, orphan stitch).
- No `mark_tenant_dirty` on Slack channel apply — sync completion enqueues dirty.
- Phase 04 walk schedule skipped by default (`CORTEX_SUBSTRATE_SKIP_WALK_SCHEDULE_V1`).
- Failure remediation blocks substrate replay job kinds → use operator Repair.
- Convergence **sweep** is safety-net enqueue only.

---

## Logging

Each slice emits one structured line: **`substrate_slice_complete`** (tenant, outcome, lane flags, epochs). Do not add per-phase duplicate telemetry on the hot path.

---

## Runtime flags (prod)

| Setting | If false |
|---------|----------|
| `cortex_post_ingestion_substrate_refresh_enabled` | Live ingest won't enqueue |
| `cortex_execution_event_triggers_enabled` | Post-ingest won't mark dirty |
| `cortex_execution_dual_lane_enabled` | Worker stalls (serial removed) |

---

## Deploy

**CI:** `backend-substrate-coherence` — waves 1–8 pytest + `substrate_ci_gates.py`.

**Post-deploy:**

```bash
cd backend && PYTHONPATH=src python scripts/substrate_post_deploy_gate.py \
  --expected-sha "$GITHUB_SHA" \
  --baseline ../DOCS/audits/baselines/substrate_truth_fizzer_wave0_baseline.json
```

**Soak (24h):** `substrate_soak_v6_v8_check.py`. **Snapshot:** `substrate_truth_audit_snapshot.py`.

---

## Common failures

| Symptom | Check |
|---------|--------|
| Raw grows, nothing else | `vector` worker up? |
| Dirty forever | lease `last_error`, truth `operational.next_retry_at` |
| Replay idle | Replay lane does not mark dirty — use live sync |
| High edges, no people merge | truth `graph_substrate.isolated_pct`, `promotion_rule_count` |
