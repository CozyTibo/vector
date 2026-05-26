# Cortex substrate — 2-minute onboarding (Wave 9)

**One sentence:** Ingest dirties the lease; the `vector` worker runs dual-lane slices that materialize canonical rows, repair identity on a cursor, promote authoritative links inline, and export a graph hash; the Substrate tab reads `substrate_truth_v1`.

---

## Five verbs (authoritative)

| Verb | What moves | Owner |
|------|------------|--------|
| **INGEST** | Raw rows + connector checkpoints | `execute_connector_sync` |
| **MATERIALIZE** | Anchors + materializations | `drain_forward_progress_backlog` |
| **REPAIR** | Org entities, candidates, repair cursor | `run_identity_substrate_repair_slice_v1` |
| **PROMOTE** | Authoritative `cortex_org_links` | `run_graph_density_promotion_pass_v1` |
| **EXPORT** | Ephemeral stable graph hash | `run_graph_projection_export_for_pipeline_v1` |

**Dirty** is not a verb on data — it is the obligation: `mark_dirty_and_enqueue_convergence_v1` after ingest (or operator Repair).

**Truth** is read-only: `GET /admin/tenants/{id}/cortex/substrate/truth` → `build_substrate_truth_v1`.

---

## Operator actions (primary nav)

| Action | API / effect |
|--------|----------------|
| View Substrate | `GET .../cortex/substrate/truth` |
| Repair | `operator_rebuild_identities_v1` — reset repair cursor + mark dirty |
| Ingest now | Connector `trigger-sync` |
| Revoke link | Explicit `soft_revoke_org_link` (only non-debug write on primary identity API) |

**Not on primary nav:** rebuild continuity, flush-to-identity, replay jobs, backfill anchors — those live under `.../cortex/debug/*` with `?debug=1`.

---

## Predict next step

Read `substrate_truth_v1.operational.next_mutation_hint` (also `next_retry_at`, topology gate, dual-lane flags). See [substrate_queue_runbook.md](./substrate_queue_runbook.md).

---

## CI / on-call

- **CI:** `backend/scripts/substrate_ci_gates.py` (waves 1–9 static laws)
- **On-call:** `substrate_truth_v1` + `continuity_audit_snapshot.py` only for substrate health
- **Contracts:** `backend/contracts/substrate_v1.yaml` + `substrate_truth_v1.schema.json`

---

## What we deleted (do not reintroduce)

- Pre-slice / event / orphan autonomous promotion
- `unlock/` imports from `execution` or `identity`
- Substrate motion from Slack admin without ingest handoff
- Primary-nav replay jobs (`identity_continuity_rebuild` is debug-only)
