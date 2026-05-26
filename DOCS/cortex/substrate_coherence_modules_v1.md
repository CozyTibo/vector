# Cortex substrate coherence modules (Wave 6)

**Purpose:** Onboarding map of the **authoritative** substrate path and the modules that implement it. Count: **18** production modules (target &lt;20).

## Authoritative motion

| Step | Module |
|------|--------|
| Post-ingest dirty | `execution/convergence_dispatch.py` → `mark_dirty_and_enqueue_convergence_v1` |
| Slice worker | `execution/run_tenant_execution.py` |
| Dual-lane convergence | `execution/dual_lane_convergence.py` |
| Identity repair + promotion | `identity/identity_substrate_repair_v1.py` |
| Graph promotion (inline) | `operational_runtime/graph_density_promotion.py` |
| Graph export | `identity/projection_export.py` |
| Event triggers (hash / ingest) | `execution/execution_event_triggers.py` |
| Operator truth | `substrate_pipeline/substrate_truth_v1.py` |
| Contract builders | `substrate_pipeline/substrate_contract_v1.py` |

## Supporting substrate pipeline

| Module | Role |
|--------|------|
| `substrate_pipeline/orchestrator.py` | TCRE/pipeline callbacks (compat `schedule_substrate_pipeline_v1` → convergence) |
| `substrate_pipeline/phase_runners.py` | Phase 02–08 runners (receipt-honest status) |
| `substrate_pipeline/repository.py` | Pipeline run persistence |
| `substrate_pipeline/substrate_deploy_contract_v1.py` | CI / post-deploy / soak contract |
| `substrate_pipeline/substrate_residue_v1.py` | Wave 6 grep gates (no runtime) |
| `substrate_pipeline/continuity_audit_snapshot.py` | Canonical operator audit JSON |
| `ingestion/post_ingestion_refresh_dispatch.py` | Ingest → `trigger_post_ingestion_execution_v1` |
| `ingestion/sync_router.py` | Connector sync entry (not `sync_executor` shim) |

## Removed in Wave 6 (do not reintroduce)

- `graph_hash_autonomous_chain` / B5 chain runner
- `post_ingestion_refresh_celery_task_id` fiction
- Duplicate `schedule_graph_density_promotion_after_identity_substrate_v1`
- Production imports of `ingestion.sync_executor` (shim remains for tests only)

## Verification

```bash
cd backend && python -m pytest tests/vector/domains/cortex/substrate_pipeline/test_substrate_wave6_residue_purge.py -q
python backend/scripts/substrate_ci_gates.py
```

See also: [substrate_queue_runbook.md](./substrate_queue_runbook.md), [cortex_substrate_collapse_plan_v1.md](../audits/cortex_substrate_collapse_plan_v1.md).
