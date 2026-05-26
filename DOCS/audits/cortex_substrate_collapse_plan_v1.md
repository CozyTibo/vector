# Cortex substrate collapse plan (v1)

**Status:** Collapse plan — **no implementation** in this document  
**Builds on:** [`cortex_minimal_substrate_reality_audit_v1.md`](cortex_minimal_substrate_reality_audit_v1.md), [`cortex_identity_reconstruction_full_system_audit_v1.md`](cortex_identity_reconstruction_full_system_audit_v1.md)  
**Objective:** Reduce Cortex from accumulated operational complexity into **one durable deterministic substrate flow** — fewer paths, fewer lies, deployable truth.

**Non-goals:** New orchestrator, identity v2, replay subsystem v2, phase framework, event DAG, ML identity.

---

## Executive summary

The minimal substrate already exists in code:

```
INGEST → mark_dirty → convergence_slice → materialize+anchor → repair_slice → promote → graph_export
```

Collapse means **removing everything that pretends to be a second substrate**, not inventing a third.

| Principle | Action |
|-----------|--------|
| One writer per concern | Single owner for dirty, repair, promotion, graph export |
| One truth surface | `substrate_truth_v1` replaces fragmented cards |
| One repair semantics | Lease cursor + `run_identity_substrate_repair_slice_v1` only |
| One promotion moment | End of repair slice only (delete duplicate schedulers) |
| Honest phases | Kill fake `COMPLETED_EMPTY`; align `phase_run.status` with receipt |
| Deploy = proof | SHA gate + Fizzer snapshot diff before/after |

**Sequencing:** Truth & gates → stop duplicate promotion → collapse operator paths → delete dead surfaces → deploy contract. **Not** a big-bang rewrite.

---

## 1. Authoritative flow collapse

### 1.1 The SINGLE authoritative runtime path

```
┌──────────────────────────────────────────────────────────────────────────┐
│ OWNER: convergence lease + vector queue                                   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  [INGEST] cortex_live: run_cortex_connector_sync_task                     │
│      → sync_router.execute_connector_sync → RawIngestionRecord            │
│      → (live incremental only) mark_dirty_and_enqueue_convergence_v1      │
│                                                                           │
│  [SUBSTRATE] vector: run_execution_slice_task                             │
│      → run_tenant_convergence_v1                                          │
│      → run_dual_lane_convergence_v1                                       │
│           Lane A: run_phase_02_canonical_v1                               │
│               → drain_forward_progress_backlog                            │
│               → materialize_raw_record                                    │
│               → upsert_identity_anchor_for_materialization                │
│           Lane B (cursor ≥ 03):                                           │
│               run_phase_03_identity_v1                                    │
│               → run_identity_substrate_repair_slice_v1  [ONLY REPAIR]     │
│               → schedule_graph_density_pass_v1 (INLINE, end of slice)     │
│               run_phase_04_graph_v1                                       │
│               → build_org_graph_projection_export_document                │
│                                                                           │
│  [SAFETY] vector: convergence.sweep (re-enqueue dirty only, no ingest)   │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Ownership boundaries (who owns what)

| Concern | **Authoritative owner** | Must NOT own it |
|---------|-------------------------|-----------------|
| **Dirty obligation** | `convergence_dispatch.mark_dirty_and_enqueue_convergence_v1` | Slack channel apply direct dirty; duplicate orchestrator |
| **Slice scheduling** | `enqueue.enqueue_tenant_convergence_v1` → `run_execution_slice_task` | Per-phase Celery coordinators (M9 dead) |
| **Canonical drain** | `drain_forward_progress_backlog` via phase 02 only | `identity_continuity_rebuild` inline drain for routine ops |
| **Anchor creation** | `upsert_identity_anchor_for_materialization` on mat | Phase 03 (projection only) |
| **Identity repair** | `run_identity_substrate_repair_slice_v1` | Replay jobs, admin backfill, exhausted rebuild job |
| **Repair cursor** | `lease.detail_json.identity_substrate_repair_v1` | Replay job rows |
| **Promotion** | `run_graph_density_promotion_pass_v1` called **once** from repair slice | Convergence worker pre-pass; orphan stitch; replay `lawful_edge_promotion`; event-trigger promotion |
| **Graph export** | `run_phase_04_graph_v1` → projection export | Replay `graph_projection_export` except debug |
| **Retries** | `schedule_convergence_retry_v1` on canonical topology_wait | Ad-hoc replay job retries |
| **Replay (raw)** | `cortex_replay` ingest task | Must not imply substrate motion |

### 1.3 Everything else becomes

| Class | Examples | Treatment |
|-------|----------|-----------|
| **Deleted** | Duplicate promotion at slice start; `identity_continuity_rebuild` routine path; Celery `regenerate_link_candidates` | Remove from hot path + operator UI |
| **Adapter-only** | Admin `trigger-sync` → same Celery task as beat | Keep one HTTP entry |
| **Read-only tooling** | `identity_continuity_diagnosis_v1`, graph_truth snapshot scripts | Keep; not control plane |
| **Reset helpers** | `reset_identity_substrate_repair_state_v1` + `mark_dirty` | Operator: 2 actions only |
| **Debug** | `replay-jobs/run` sync for one-off audit; `graph-density-promotion/run` force pass | Admin-debug namespace; hidden from primary UX |

### 1.4 Critical collapse: duplicate promotion per slice

**Today (broken):** `run_tenant_convergence_v1` calls `schedule_graph_density_promotion_on_convergence_worker_v1` **before** dual-lane work; repair slice calls `schedule_graph_density_pass_v1` **again** after backfill/regen.

**Files:**
- `execution/run_tenant_execution.py` (~lines 94–102)
- `identity/identity_substrate_repair_v1.py` (~lines 175–182)
- Also: `execution_event_triggers.schedule_graph_density_promotion_after_identity_substrate_v1`, `graph_orphan_continuity.run_continuity_stitching_pass_v1`

**Collapse rule:** Promotion runs **only** inside `run_identity_substrate_repair_slice_v1` when `entities_upserted > 0` OR candidate regen ran OR `force=repair_owed`. Delete all other autonomous promotion hooks.

**Why this existed:** Promotion backlog when repair was fragmented. **Why it must die:** Explains 5× duplicate auth edges and “graph moving” while identity health flat.

---

## 2. Identity flow collapse

### 2.1 ONE identity runtime model

| Layer | Single artifact / function |
|-------|---------------------------|
| **Evidence** | `cortex_canonical_identity_anchors` |
| **Projection** | `extract_identity_primitives` (ephemeral) |
| **Handles** | `upsert_org_entity` via `run_anchor_handle_backfill` |
| **Candidates** | `run_anchor_continuity_candidate_regeneration` |
| **Truth edges** | `promote_candidate_to_authoritative_link` |
| **Repair** | `run_identity_substrate_repair_slice_v1` |
| **Health** | `evaluate_identity_substrate_health_v1` |
| **Cursor** | `identity_substrate_repair_v1` on lease |

No “person” table. No second repair orchestrator.

### 2.2 ONE repair model

```
each convergence slice (phase 03 budget):
  load health + repair state from lease
  paginated backfill (anchor_offset += batch)
  if exhausted OR (entities upserted && no candidates):
      candidate regen (full scan)
  if work done OR health repair owed:
      promotion pass (inline, capped)
  persist lease state + health on phase receipt
  resolve_phase_03_outcome_v1 (honest)
```

**Exhaustion:** `anchor_offset >= anchors_total` → set `anchor_backfill_exhausted=true` → regen once per cycle.

**Operator “repair”:** NOT a different algorithm — only:

1. `reset_identity_substrate_repair_state_v1` (offset=0, exhausted=false)
2. `mark_dirty_and_enqueue_convergence_v1` (reason=`operator:repair_reset`)
3. Optionally run **K slices synchronously** in admin-debug (same function, loop), not a Celery replay job

### 2.3 ONE cursor

Only `lease.detail_json.identity_substrate_repair_v1`:

```json
{
  "anchor_offset": 0,
  "anchor_backfill_exhausted": false,
  "anchors_total": 21544,
  "last_slice_entities_upserted": 0,
  "updated_at": "..."
}
```

Delete: using `CortexOrgLinkReplayJob` as repair progress indicator.

### 2.4 ONE promotion model

- Entry: `run_graph_density_promotion_pass_v1` only
- Scheduling: `schedule_graph_density_pass_v1` — **inline**, no Celery (M9 already killed `app.tasks.cortex_graph_density_promotion`)
- Fair rule order: `list_promotable_link_candidates_fair_by_rule_v1` (keep)
- Cap: `cortex_graph_density_promotion_max_per_pass` (keep; consider raising only after duplicate hooks removed)

Delete: `lawful_edge_promotion` replay job kind for routine ops; `schedule_graph_density_promotion_on_convergence_worker_v1`.

### 2.5 ONE truth model

**`substrate_truth_v1`** (new aggregate, read-only builder — plan only):

| Field group | Source |
|-------------|--------|
| `motion` | lease status, cursor, obligation_epoch, last_slice_at |
| `canonical` | drain outcome, drainable count, deferral breakdown |
| `identity_health` | `evaluate_identity_substrate_health_v1` |
| `repair` | repair state dict |
| `identity_counts` | anchors, entities, candidates, auth_links, distinct rules |
| `graph` | isolated_pct, largest_component_pct, auth_links_by_rule (from graph_truth SQL) |
| `last_slice_delta` | entities_upserted, candidates_delta, promotions_applied, projection_hash_changed |
| `deploy` | optional: ECS SHA match flag |

### 2.6 Operator actions (only three)

| Action | Implementation | NOT |
|--------|----------------|-----|
| **Reset repair cursor** | `reset_identity_substrate_repair_state_v1` + mark dirty | `identity_continuity_rebuild` |
| **Mark dirty / run slice** | `mark_dirty_and_enqueue_convergence_v1` | `schedule_substrate_pipeline_v1` duplicate |
| **Inspect health** | GET `substrate_truth_v1` (new) or snapshot script | Control plane link-count cards alone |

**Collapse `rebuild_identities`:** Keep name in operator UI but implement as **reset + mark dirty** (remove `enqueue_rebuild_identities_from_anchors_v1` → Celery replay job).

### 2.7 Path consolidation table

| Current path | Verdict |
|--------------|---------|
| Phase 03 `run_identity_substrate_repair_slice_v1` | **KEEP** — sole mutator |
| `rebuild_identities` → `identity_rebuild_from_anchors` replay job | **COLLAPSE** → reset + dirty |
| `identity_continuity_rebuild` | **DELETE** from operator docs; **DEBUG-ONLY** “canonical+identity refresh” with scary banner |
| Admin `backfill/from-canonical-anchors` | **DELETE** from primary UI; debug API only |
| Celery `regenerate_link_candidates_task` | **DELETE** task registration |
| Celery `replay_authoritative_links_task` | **DELETE** or debug-only |
| `graph_hash_autonomous_chain_v1` | **DELETE** from prod flags (default off); keep unit tests |
| `run_continuity_stitching_pass_v1` | **DELETE** from autonomous triggers; keep classify as read-only |
| Legacy `regenerate_link_candidates` (non-anchor) in replay `candidate_regen` | **DELETE** code path |

---

## 3. Queue / worker collapse

### 3.1 Minimal queue truth

**Target: two operational lanes + one safety task on substrate queue.**

| Queue | Role | Tasks | Authoritative? |
|-------|------|-------|----------------|
| **`cortex_live`** | Ingestion | `vector.cortex.ingestion.run_sync`, scheduler tick may stay on `vector` | **Yes** — live ingest |
| **`cortex_replay`** | Isolated replay ingest | `vector.cortex.ingestion.run_sync_replay` | **Compatibility** — raw only, no dirty |
| **`vector`** | Substrate | `run_slice`, `convergence.sweep`, optional `run_org_link_replay_job` (audit) | **Yes** — all substrate motion |

**Beat on `vector`:** `scheduler_tick`, `convergence.sweep` — acceptable if ingestion workers also listen to `vector` OR beat runs on substrate fleet only (document one model).

### 3.2 Classification of all queues / tasks (substrate scope)

| Item | Class | Notes |
|------|-------|-------|
| `cortex_live` | Authoritative | Must have dedicated worker in prod |
| `cortex_replay` | Compatibility | Do not use for “fix prod” |
| `vector` | Authoritative | Must consume or substrate stalls |
| M9 dead modules (12) | Dead | CI guard only |
| `run_org_link_replay_job` | Dangerous | Looks like repair; collapse to audit |
| `regenerate_link_candidates` Celery | Dead weight | Duplicate regen |
| `cortex_admin_snapshot` tasks | Hidden | Not substrate; OK on vector |
| `cortex_ingestion.verify_tenant` | Debug | Optional |

### 3.3 “Deploy works locally but not prod”

| Cause | Collapse fix |
|-------|--------------|
| Dev compose: one worker listens to all queues | **Document** prod split; CI smoke with split queues |
| API deployed, substrate worker old | Mandatory `probe_prod_ecs_deploy_v1` both services |
| `cortex_execution_event_triggers_enabled=false` in prod | Substrate truth exposes flag |
| Post-ingest disabled | Same |
| Ingestion worker missing `cortex_live` | ECS task definition check in deploy gate |
| Replay used without manual dirty | Operator docs + UI warning |
| Promotion ran on old worker (pre-fair-schedule) | SHA gate |

### 3.4 Invisible failure modes (queue semantics)

| Symptom | Cause |
|---------|-------|
| Raw grows, nothing else | `vector` not consumed |
| Dirty forever, no slice | enqueue failed / worker exception loop |
| Replay job `queued` forever | Wrong queue or worker not running `vector` |
| Job `completed`, substrate unchanged | Replay job is not repair slice — **truth collapse** |

---

## 4. Operational truth collapse

### 4.1 Problem

Truth is fragmented across:

- `cortex_tenant_convergence_leases`
- `cortex_substrate_pipeline_runs` / phase runs
- `cortex_org_link_replay_jobs`
- Phase receipts (`COMPLETED_EMPTY`)
- Identity control plane cards
- AA panel (downstream — **demote**)
- Graph inspectors

Operators read the wrong layer and conclude “completed.”

### 4.2 ONE authoritative substrate state

**Primary:** `substrate_truth_v1` built from lease + SQL counts + health + last slice receipt embedded in `lease.detail_json.substrate_last_slice_v1` (planned field).

**Secondary (debug only):**

| Source | Use |
|--------|-----|
| `cortex_substrate_pipeline_runs` | Historical run viewer — **not** health |
| `cortex_org_link_replay_jobs` | Audit trail after collapse — **not** progress |
| Phase run rows | Forensics — receipt outcome > `status` column |
| AA panel | Downstream product gate — **never** substrate sign-off |
| Control plane `persona_bindings` count | Vanity without `distinct_promotion_rules` |

### 4.3 What operators trust (single screen)

```
Substrate status: HEALTHY | DEGRADED | BROKEN | STALLED
Canonical: DRAINING | TOPOLOGY_STALL | STRUCTURALLY_INCOMPLETE
Repair: offset / total | exhausted | last_slice_upserts
Identity: anchors | entities | candidates | auth_pairs | rules (≥3?)
Graph: isolated% | largest_component%
Motion: dirty | last_slice_at | worker_sha == api_sha
```

**Red rules:**

- `isolated_pct > 90%` → cannot show “graph healthy”
- `distinct_promotion_rules < 2` → cannot show “identity healthy”
- `COMPLETED_EMPTY` with `DEGRADED` → show **FAILED** in UI even if DB receipt old

### 4.4 Collapse admin surfaces

| Keep | Demote / merge |
|------|----------------|
| New **Substrate** overview tab (truth v1) | Identity control plane as primary |
| People (clusters) | Flat 7k handle list as default |
| Inspect → identity diagnosis | Replay job list as main actions |
| Connector ingest status | Duplicate pipeline-run progress bar |

---

## 5. Phase semantics collapse

### 5.1 Current lies

| Outcome | Lie |
|---------|-----|
| `COMPLETED_EMPTY` | “Success” while degraded / zero delta |
| `phase_run.status=completed` + receipt `BLOCKED` | Phase 02 topology_wait |
| Phase 04 `COMPLETED` + climbing `edge_count` | Duplicate promotions |
| `topology_wait` in lease + cursor on 03 | Looks stuck; may be OK with R1 |

### 5.2 Minimal truthful semantics (substrate phases only)

| Phase | Outcomes allowed | Meaning |
|-------|------------------|---------|
| **02 Canonical** | `COMPLETED` (mats>0), `BLOCKED` (topology_wait, 0 mats), `FAILED` | Never empty-complete |
| **03 Identity** | `COMPLETED` (delta), `IN_PROGRESS` (repair not exhausted), `FAILED` (exhausted+degraded+0 delta), `SKIPPED` (no bundle) | **Delete `COMPLETED_EMPTY`** as success label — map to `IN_PROGRESS` or `FAILED` |
| **04 Graph** | `COMPLETED` (hash changed), `SKIPPED` (identity zero delta policy), `FAILED` (export error) | Never “completed” if isolated_pct unchanged and identity failed |

**Align DB:** `phase_run.status` must match receipt outcome class (blocked/failed/waiting/completed).

### 5.3 Outcomes to disappear

| Outcome | Replacement |
|---------|-------------|
| `COMPLETED_EMPTY` (as green) | `IN_PROGRESS` or `FAILED` with `blocked_reason` |
| Auto-promote COMPLETED→COMPLETED_EMPTY on processed_count=0 | Use explicit `IN_PROGRESS` for phase 03 |

### 5.4 Phases become convergence-native

- No separate phase Celery tasks (already M9 dead)
- Phase 03 **always** runs repair slice when cursor ≥ 03 — not optional sidecar
- Phase 04 skip **only** when `should_skip_phase_04_after_identity_v1` AND health not degraded

### 5.5 `topology_wait` rename (operator)

Expose as **`CANONICAL_STALL`** with sub-reason:

- `drainable>0` → worker will retry
- `drainable=0` → `STRUCTURALLY_INCOMPLETE` (identity may still run)

---

## 6. Graph collapse

### 6.1 Smallest truthful graph

**Persisted truth:**

- `cortex_org_entities` (handles)
- `cortex_org_links` where `link_authority=authoritative`
- Optional: `cortex_org_primitive_instances` (execution envelopes on handles — keep for later, not required for minimal ingest→graph proof)

**Ephemeral:**

- `OrgGraphProjectionV1` export document + stable hash (phase 04 receipt)

**NOT in minimal substrate:**

- Island registry as graph truth
- Walk-scheduling coupling to graph export
- Candidate rows as graph edges

### 6.2 What graph IS

**Identity continuity graph:** authoritative `org.persona_belongs_to_handle` edges only — cross-tool merge evidence.

**NOT:** PR/repo/channel execution topology (deferred out of scope).

### 6.3 Graph export should stop

- Exporting **all** 7k nodes when 96% isolated — export OK for hash, **KPI must not be node_count**
- Triggering walk schedules from graph hash change in substrate collapse scope — **disable** from phase 04 for substrate sign-off (walks are out of scope but pollute “graph moved” signals)

### 6.4 KPIs that die forever

| Dead KPI | Replacement |
|----------|-------------|
| `edge_count` monotonic | `unique_auth_pairs` |
| `node_count` | `entities_in_largest_auth_component` |
| `pending_candidates` alone | `promotable_candidates` + `distinct_promotion_rules` |
| Graph “density ρ” global | `largest_component_entity_pct` |
| Phase 04 `processed_count` | `projection_hash_changed` + `isolated_pct_delta` |

### 6.5 Minimal graph acceptance (Fizzer)

- `distinct_promotion_rules >= 3`
- `largest_component_entity_pct >= 10%` (or documented waiver)
- `unique_auth_pairs` grows only when new pairs promoted (dedupe enforced)
- `projection_stable_hash` changes IFF auth set changed

---

## 7. Deploy / validation collapse

### 7.1 Minimal pre-deploy gate (mandatory)

```bash
# CI
verify_m9_dead_celery_modules_absent_v1
pytest tests for phase_03 outcome + promotion single-hook (after impl)

# Pre-push to prod
git rev-parse HEAD  # record SHA
```

### 7.2 Minimal post-deploy gate (mandatory, <30 min)

```bash
# 1. ECS alignment
probe_prod_ecs_deploy_v1(expected_sha=$DEPLOY_SHA)
# require api_ok && worker_ok

# 2. Substrate snapshot (Fizzer)
python backend/scripts/identity_continuity_audit_snapshot.py --tenant $FIZZER --json > /tmp/post.json
python backend/scripts/graph_truth_audit_snapshot.py --tenant $FIZZER --json >> /tmp/post.json

# 3. Diff vs committed baseline in DOCS/audits/baselines/
# FAIL if: distinct_promotion_rules regresses, isolated_pct increases, anchors_without_entity increases

# 4. Motion proof
# trigger one incremental sync OR mark_dirty
# within 10m: obligation_epoch++, lease.last_slice_at updated, repair offset moved OR exhausted cycle
```

### 7.3 Minimal substrate E2E contract (V1–V9)

| ID | Check | Pass criteria |
|----|-------|---------------|
| V1 | Workers consume | `vector` + `cortex_live` queue depth drains |
| V2 | Ingest → dirty | obligation_epoch bumps after live sync |
| V3 | Mat → anchor | anchor count ≥ mat count (person/user anchors) over 24h window |
| V4 | Repair moves cursor | `anchor_offset` increases until exhausted |
| V5 | Regen on exhaustion | new candidate batch hash when anchors changed |
| V6 | Promotion diversity | ≥3 `rule_id` on auth links |
| V7 | Graph hash | changes when auth pairs change |
| V8 | Isolation | `isolated_pct < 90%` or waiver ticket |
| V9 | People spot-check | sample engineer shows ≥2 connector IDs in cluster |

### 7.4 People UI as validation (not substrate storage)

- Union-find on authoritative edges
- Show **cluster** not 7390 singleton cards
- Spot-check after V6 passes

### 7.5 What deploy means after collapse

**Deploy succeeded** IFF:

- SHA match
- Snapshot diff green
- V4–V7 trending correct within 24h soak (not necessarily instant on 21k anchors)

**Deploy failed** even if:

- Pipeline run says completed
- Replay job says completed
- AA partial pass

---

## 8. DELETE list (ruthless)

### 8.1 Runtime / scheduling (delete from hot path)

| Item | Location |
|------|----------|
| Pre-slice promotion hook | `execution/run_tenant_execution.py` |
| Post-substrate event promotion | `execution_event_triggers.schedule_graph_density_promotion_after_identity_substrate_v1` |
| Orphan stitch promotion | `graph_orphan_continuity.run_continuity_stitching_pass_v1` autonomous trigger |
| `graph_hash_autonomous_chain` prod enable | `settings.cortex_graph_hash_autonomous_chain_enabled` default false + remove callers |
| `schedule_substrate_pipeline_v1` as ingest handoff | `substrate_pipeline/orchestrator.py` — callers → `mark_dirty` only |

### 8.2 Celery tasks (delete registration)

| Task | Module |
|------|--------|
| `vector.cortex.identity.regenerate_link_candidates` | `app/tasks/cortex_org_link_jobs.py` |
| `vector.cortex.identity.replay_authoritative_links` | `app/tasks/cortex_org_link_jobs.py` |
| (already dead) M9 modules | per `scheduling.M9_DEAD_*` |

Keep: `run_org_link_replay_job` **only** if reduced to audit export debug.

### 8.3 Replay job kinds (delete from product)

| `job_kind` | Action |
|------------|--------|
| `identity_continuity_rebuild` | Delete operator entry |
| `identity_rebuild_from_anchors` | Delete — replaced by reset+dirty |
| `lawful_edge_promotion` | Delete — promotion only in repair slice |
| `candidate_regen` | Debug-only |
| `authoritative_replay` | Debug-only (hash) |
| `graph_projection_export` | Debug-only |

### 8.4 HTTP / operator APIs

| Route / action | Action |
|----------------|--------|
| `POST .../backfill/from-canonical-anchors` | Debug namespace |
| `POST .../replay-jobs/enqueue` (generic) | Debug namespace |
| `rebuild_identities` → Celery replay | Rewrite to reset+dirty |
| `OPERATIONAL_REPLAY_CANONICAL_GUIDE` “prefer identity_continuity_rebuild” | Delete text |
| `flush-rerun-to-identity` | Already forbidden — remove docs |
| Admin graph-density-promotion as primary | Debug-only |

### 8.5 Functions / code paths

| Symbol | Action |
|--------|--------|
| `run_identity_continuity_rebuild` | Demote to `debug_full_substrate_refresh_v1` single file, not linked from UI |
| `enqueue_rebuild_identities_from_anchors_v1` | Delete after operator rewrite |
| `run_identity_handles_and_candidates_refresh` as public API | Internal to debug refresh only |
| Legacy `regenerate_link_candidates` without anchor continuity | Delete branch in replay runtime |
| `schedule_graph_density_promotion_on_convergence_worker_v1` | Delete |

### 8.6 Config / semantics

| Item | Action |
|------|--------|
| `cortex_post_ingestion_substrate_refresh_debounce_*` | Delete settings or implement (pick delete) |
| `cortex_graph_density_promotion_schedule_countdown_seconds` | Delete (inline only) |
| `cortex_graph_density_promotion_on_convergence_enabled` | Delete setting after hook removed |
| Control plane freshness on replay jobs | Remove as health signal |

### 8.7 UI cards / KPIs

| KPI | Action |
|-----|--------|
| Edge count badge | Delete |
| Raw−mat backlog without drainable | Delete |
| Persona_bindings without rule breakdown | Delete |
| Pipeline run “phase completed” strip | Demote |
| AA panel on substrate overview | Delete |

### 8.8 Scripts (archive, not delete repo yet)

| Path | Action |
|------|--------|
| `backend/scripts/archive/continuity_proofs/*` (39 files) | Already archived — **ban** from operator runbooks |
| `backend/scripts/prod_substrate_proof_queries.py` | Deprecated — use `continuity_audit_snapshot.py` |
| `backend/scripts/continuity_proof_panel.py` | Merge into audit snapshot only |

**Keep scripts:**

- `continuity_audit_snapshot.py`
- `identity_continuity_audit_snapshot.py`
- `graph_truth_audit_snapshot.py`

### 8.9 Status fields

| Field | Action |
|-------|--------|
| `phase_run.status` when receipt is BLOCKED/FAILED | Fix to match |
| `COMPLETED_EMPTY` in operator green lists | Remove |
| `post_ingestion_refresh_celery_task_id` diagnostic | Remove or rename |

---

## 9. Minimal target state

### 9.1 Boring architecture diagram

```
                    ┌─────────────┐
                    │ cortex_live │
                    └──────┬──────┘
                           │ raw
                           ▼
              mark_dirty_and_enqueue (vector)
                           │
                           ▼
              ┌────────────────────────────┐
              │ ONE convergence slice       │
              │  canonical drain → anchors    │
              │  repair slice → promote     │
              │  graph export → hash        │
              └────────────────────────────┘
                           │
                           ▼
              substrate_truth_v1 (read)
```

### 9.2 Invariant laws (substrate)

| ID | Law |
|----|-----|
| L1 | Only `mark_dirty_and_enqueue` starts substrate motion after live ingest |
| L2 | Anchors created only in `materialize_raw_record` |
| L3 | Only `run_identity_substrate_repair_slice_v1` mutates handles/candidates/promotion in autonomous path |
| L4 | Promotion ≤1× per repair slice; fair rule rotation |
| L5 | At most one active authoritative link per (source, target, link_type) |
| L6 | Phase 03 never reports success when `phase_03_forbids_completed_empty_v1` |
| L7 | Graph export skipped when identity zero-delta AND degraded |
| L8 | `substrate_truth_v1.status=BROKEN` blocks claiming “substrate healthy” in UI |
| L9 | Deploy without snapshot diff = invalid deploy |

### 9.3 Operator mental model (one sentence)

> “Ingest dirties the lease; the vector worker runs slices that materialize, repair identity on a cursor, promote inline, and export graph; Substrate tab tells the truth.”

---

## 10. Implementation waves (ordered, still not “rewrite”)

### Wave 0 — Truth (no behavior change yet) — **DONE**

- [x] `build_substrate_truth_v1` — `backend/src/vector/domains/cortex/substrate_pipeline/substrate_truth_v1.py`
- [x] `GET /admin/tenants/{tenant_id}/cortex/substrate/truth` — `admin_cortex_operator.py`
- [x] Operator overview embeds `substrate_truth` — `operator_admin_overview.py`
- [x] UI: `OperatorSubstrateTruthSection` on overview page
- [x] Runbook: `DOCS/cortex/substrate_queue_runbook.md`
- [x] Snapshot script: `backend/scripts/substrate_truth_audit_snapshot.py`
- [x] Baseline template: `DOCS/audits/baselines/substrate_truth_fizzer_wave0_baseline.json` (populate from prod via script)

**Wave 0 does not** change repair/promotion behavior (Wave 1).

### Wave 1 — Stop the bleeding

- Remove pre-slice `schedule_graph_density_promotion_on_convergence_worker_v1`
- Remove event-trigger duplicate promotion
- Enforce `resolve_phase_03_outcome_v1` on all paths
- Fix `phase_run.status` vs receipt for phase 02/03

### Wave 2 — Collapse operator paths

- `rebuild_identities` → reset cursor + mark dirty (no replay job)
- Hide replay job UI except debug
- Demote `identity_continuity_rebuild` to debug script
- Remove admin backfill from primary nav

### Wave 3 — Delete dead weight

- Unregister legacy Celery regen/replay tasks
- Delete orphan stitch autonomous promotion
- Remove orphaned debounce settings
- Archive references in control plane guide

### Wave 4 — Graph truth

- Phase 04 receipt uses isolation + hash delta only
- Disable walk trigger from phase 04 for substrate KPI (optional flag)
- People UI clusters

### Wave 5 — Deploy contract

- CI: substrate outcome tests + M9
- CD: mandatory probe + snapshot diff
- 24h Fizzer soak: V6–V8

**Each wave is independently shippable.** No new orchestrator at any wave.

---

## 11. Why accumulated complexity existed (honest)

| Accumulated thing | Existed because | Collapse answer |
|-------------------|-----------------|-----------------|
| Replay jobs | Async repair when worker truth was weak | Lease cursor + slice truth |
| `identity_continuity_rebuild` | Needed canonical drain + identity in one button | Dual-lane already runs both; operator reset cursor instead |
| Duplicate promotion | Backlog + fragmented repair | Single promotion moment |
| `COMPLETED_EMPTY` | Avoid looking blocked | Honest IN_PROGRESS/FAILED |
| Pipeline run mirror | Operator wanted “run” metaphor | Lease is the run |
| 39 proof scripts | Each phase needed evidence before unified audit | One snapshot script |
| Graph hash chain | Bypass stuck FSM | Fix FSM truth instead |
| Orphan stitch | Push promotion without phase 03 | Delete autonomous stitch |
| AA panel on substrate | Milestone tracking | Separate downstream sign-off |

---

## 12. Success criteria — Waves 0–5 (coherence gate)

**Waves 6–9 MUST NOT start until all of these are true on Fizzer (prod):**

| Gate | Evidence |
|------|----------|
| G0 | `substrate_truth_v1` is primary operator surface |
| G1 | Zero autonomous promotion hooks outside repair slice |
| G2 | Phase 03 honest outcomes; no green `COMPLETED_EMPTY` while degraded |
| G3 | `rebuild_identities` = reset + dirty only; no routine replay jobs |
| G4 | V6–V8 pass: ≥3 promotion rules, isolation &lt;90% (or signed waiver), graph hash tracks auth |
| G5 | Post-deploy snapshot diff mandatory and green for 2 consecutive deploys |
| G6 | No operator dependency on `identity_continuity_rebuild` for 14 days |

Substrate **coherence** is done when:

1. Authoritative path explainable in **&lt; 60 seconds**.
2. Duplicate promotion hooks = **zero** in `grep schedule_graph_density`.
3. Routine repair = lease cursor only.

---

# PART II — DOMAIN PURGE WAVES (6–9)

**Objective class:** complexity elimination — not more architecture.  
**Rule:** If the authoritative path replaced it, runtime does not depend on it, validation covers it, and truth exposes it → **delete**.

---

## Purge classification (used in Waves 6–9)

| Class | Meaning | Action |
|-------|---------|--------|
| **DEAD** | Unreachable, M9-tombstoned, or zero prod callers | Delete code + routes + flags |
| **COMPAT** | Shim to authoritative path | Inline caller → delete shim |
| **UNUSED** | No prod telemetry / grep callers only in tests | Delete or archive |
| **EXPERIMENT** | Feature flag off, proof-only | Delete module + flag |
| **SUPERSEDED** | Replaced by lease repair / truth v1 | Delete after grep clean |
| **DEBUG** | Legitimate forensics | Move under `debug/` namespace; ban from hot path |
| **KEEP** | Authoritative substrate | Protect |

---

## Wave 6 — Domain residue purge

**Goal:** Remove dead or obsolete substrate/runtime residue so the tree matches what actually runs.

### 6.1 Entry gate

Waves 0–5 complete + G0–G6 above.

### 6.2 Residue inventory (substrate-scoped)

#### DEAD — delete

| Target | Location / symbol | Runtime impact |
|--------|-------------------|----------------|
| M9 Celery modules (12) | `scheduling.M9_DEAD_*` | None — already absent; keep CI guard |
| `flush_rerun_to_identity` task name | M9 registry | None |
| `regenerate_link_candidates_task` | `app/tasks/cortex_org_link_jobs.py` | Break only debug callers |
| `replay_authoritative_links_task` | same | Break only debug callers |
| Legacy candidate regen lane | `org_link_replay_runtime` `"legacy_rule_rows"` branch | None if anchor continuity only |
| `graph_hash_autonomous_chain` callers | `substrate_pipeline/graph_hash_autonomous_chain.py` | None if flag off + tests updated |
| Orphan stitch Celery module | M9 `cortex_orphan_continuity_stitch` | None |
| Post-ingest debounce settings | `settings.py` unused keys | None |
| `post_ingestion_refresh_celery_task_id` fiction | `post_ingestion_refresh_dispatch.py` | Admin diagnostic only |
| `continuity_proof_panel.py` standalone | `backend/scripts/` | Use `continuity_audit_snapshot.py` |
| `prod_substrate_proof_queries.py` | `backend/scripts/` | Deprecated exit already |
| 39× `continuity_p*_proof.py` | `scripts/archive/continuity_proofs/` | None — already archived |
| `unlock/step*` wedge scripts | `domains/cortex/unlock/` | None in autonomous path |
| `substrate_autonomous_progression.py` hot-path refs | catalog only | Delete imports from admin KPIs |

#### COMPAT — inline then delete

| Target | Replace with |
|--------|----------------|
| `ingestion/sync_executor.py` | Direct `sync_router.execute_connector_sync` |
| `post_ingestion_refresh_dispatch` alias chain | Direct `mark_dirty_and_enqueue_convergence_v1` |
| `schedule_substrate_pipeline_v1` | Direct `mark_dirty_and_enqueue_convergence_v1` |
| `admin.py` `connector_sync` enqueue shims | REST `trigger-sync` only |
| `attention_items_to_legacy_lines` | Remove; use structured attention items only |
| `convergence/lease.py` duplicate of execution lease | Single lease module (audit first) |

#### SUPERSEDED — delete after Wave 2

| Target | Superseded by |
|--------|----------------|
| `run_identity_continuity_rebuild` | Dual-lane + repair slice (+ debug-only full refresh) |
| `enqueue_rebuild_identities_from_anchors_v1` | reset + dirty |
| `run_identity_handles_and_candidates_refresh` public | repair slice internals |
| `CortexOrgLinkReplayJob` as progress UI | lease `identity_substrate_repair_v1` |
| `build_identity_control_plane` as primary truth | `substrate_truth_v1` |
| `OPERATIONAL_REPLAY_CANONICAL_GUIDE` | Substrate runbook (1 page) |
| `identity_substrate_projection_receipt` duplicate fields | Single repair receipt on lease slice |
| Per-phase proof modules `continuity_p0_*` (non-snapshot) | `continuity_audit_snapshot.py` |

#### EXPERIMENT — delete

| Target | Notes |
|--------|-------|
| `graph_hash_autonomous_chain_v1` | Bypass FSM — failed experiment |
| `pipeline_continuation` table writes | Frozen; delete reads from admin KPIs |
| `substrate_runtime_maturity` scoring on overview | Vanity |
| `wave_s5_cleanup_v1` verify hooks in prod UI | CI only |
| Multiple `cesp_*_gate` on substrate overview | Downstream; strip from substrate tab |

#### DEBUG — quarantine (not delete yet)

| Target | Namespace |
|--------|-----------|
| `execute_org_link_replay_job` sync API | `/admin/.../cortex/debug/...` |
| `authoritative_replay` hash job | debug |
| `graph_projection_export` replay job | debug |
| `admin_cortex_identity_backfill_from_canonical_anchors` | debug |
| `graph-density-promotion/run` force pass | debug |

### 6.3 Removal sequencing (Wave 6)

| Step | Action | Risk |
|------|--------|------|
| 6.1 | Grep gate: no imports of targets marked DEAD | CI |
| 6.2 | Remove Celery task registrations + admin routes to deleted tasks | Low |
| 6.3 | Delete compat shims (sync_executor, orchestrator wrapper) | Medium — run ingest e2e |
| 6.4 | Delete `graph_hash_autonomous_chain` + flag | Low |
| 6.5 | Delete legacy replay regen branch | Low |
| 6.6 | Move debug APIs behind `debug` prefix; 410 old paths | Medium — update frontend |
| 6.7 | Delete archived proof scripts from repo (optional) or `.cursorignore` | None |

### 6.4 Wave 6 exit criteria

- `domains/cortex/identity/` file count reduced ≥15% (substrate modules only)
- No `schedule_graph_density` outside repair slice + debug route
- `verify_m9_*` + new `verify_no_substrate_residue_v1` grep gates green
- Onboarding doc lists **&lt;20** substrate-relevant modules

---

## Wave 7 — Substrate API / contract collapse

**Goal:** One concept → one shape. Stop representing the same truth four ways.

### 7.1 Entry gate

Wave 6 complete + Fizzer snapshot stable 7 days.

### 7.2 Contract consolidation map

| Concept | Collapse to | Delete / merge from |
|---------|-------------|---------------------|
| **Substrate truth** | `substrate_truth_v1` | `identity_control_plane_v1`, `continuity_overview` substrate slice, `semantic_readiness` duplicate KPIs, `operational_truth_model_v1` split tracks |
| **Identity health** | `identity_substrate_health_v1` (embedded in truth) | Sparse honesty cards, raw link counts |
| **Repair progress** | `identity_substrate_repair_v1` on lease | Replay job `summary_json`, backfill run rows as primary |
| **Repair receipt** | `substrate_slice_receipt_v1` (one schema) | `build_identity_substrate_projection_receipt_v1`, phase 03 `output_json` forest, org link L-class receipts for repair |
| **Promotion result** | `promotion_pass_v1` sub-object in slice receipt | `graph_density_promotion_schedule` duplicate on lease (keep summary only) |
| **Graph truth** | `graph_substrate_v1` | `graph_truth_metrics_v1` + projection export duplicate counts |
| **Phase outcome** | `phase_receipt_v1` (unified enum) | `PHASE_OUTCOME_*` + `phase_run.status` mismatch |
| **Canonical stall** | `canonical_lane_v1` sub-object | `topology_wait` string soup in 3 places |
| **Ingest handoff** | `ingest_handoff_v1`: `{ dirty_enqueued, obligation_epoch }` | `post_ingestion_refresh_celery_task_id`, debounce fields |

### 7.3 Admin API collapse

| Before | After |
|--------|-------|
| Identity control plane + continuity overview + semantic readiness panel | **GET** `/cortex/substrate/truth` |
| 6 replay job endpoints | **DEBUG** `/cortex/debug/replay/...` (max 2) |
| Graph density promotion run | **DEBUG** only |
| Backfill from anchors | **DEBUG** only |
| People directory + inspect | **GET** `/cortex/people` + `/cortex/people/{id}` (unchanged surface, unified backend builder) |

### 7.4 Pydantic / OpenAPI

- One OpenAPI fragment: `contracts/substrate_v1.yaml`
- Deprecate `identity_admin.yaml` duplicate fields (version bump)
- Admin handlers: thin — call `build_substrate_truth_v1`, no local SQL

### 7.5 Wave 7 exit criteria

- Single JSON schema checked in CI (`substrate_truth_v1.schema.json`)
- Frontend Overview reads one endpoint
- Zero duplicate `auth_links` count fields across responses
- Phase 03/04 receipts validate against `phase_receipt_v1`

---

## Wave 8 — Operational simplicity pass

**Goal:** Every mutation is owned, scheduled, and observable — no surprises.

### 8.1 Entry gate

Wave 7 contracts frozen + docs updated.

### 8.2 Hidden behavior elimination checklist

| Hidden behavior | Owner today | Collapse |
|-----------------|-------------|----------|
| Auto promotion pre-slice | `run_tenant_execution` | **Deleted** (Wave 1) |
| Auto promotion on event trigger | `execution_event_triggers` | **Deleted** |
| Auto promotion orphan stitch | `graph_orphan_continuity` | **Deleted** |
| Convergence sweep enqueue | `sweep.py` | **KEEP** — document as safety net only |
| Slack channel dirty without enqueue | `admin.py` | **DELETE** dirty; enqueue only via sync complete |
| `canonical_identity_may_proceed_despite_topology` | gate | **KEEP** — expose in truth blob with reason |
| Dual-lane R1 decoupling | settings | **KEEP** — default on; truth shows `execution_lane_ran_despite_canonical_stall` |
| Replay ingest no dirty | replay task | **KEEP** — banner in replay UI |
| Phase 04 walk schedule on hash change | phase 04 | **DISABLE** for substrate (`cortex_substrate_skip_walk_schedule_v1`) |
| `schedule_convergence_retry` storm cooldown | canonical | **KEEP** — surface `next_retry_at` on truth |
| Failure remediation replay retry | `failure_remediation` | **Strip** substrate identity class |
| Implicit supersede queued replay jobs | `continuity_rebuild` | **DELETE** with replay job removal |

### 8.3 Mutation contract (every path must answer)

Template enforced in code comments + runbook:

```
OWNER:      <module.function>
TRIGGER:    <ingest | slice | operator_reset | debug_force>
MUTATES:    <table/list>
OBSERVABLE: <lease field | truth field | receipt>
IDEMPOTENT: <yes/no + key>
```

Apply to all remaining mutators (should be **&lt;10** functions).

### 8.4 Logging / telemetry collapse

- One structured log line per slice: `substrate_slice_complete` with truth summary
- Delete: per-phase duplicate telemetry paths (`execution_path_telemetry` keep once)
- Ban: new `surface_kind` strings without schema registry

### 8.5 Wave 8 exit criteria

- Substrate runbook **≤3 pages**
- All mutators listed in runbook with OWNER/TRIGGER/OBSERVABLE
- No background task modifies `cortex_org_links` outside promotion pass + explicit revoke API
- Operator can predict next mutation from lease state without reading code

---

## Wave 9 — Final domain shape

**Goal:** Document and enforce the **final** Cortex substrate — explainable in **&lt;2 minutes**.

### 9.1 Entry gate

Waves 6–8 complete + 30-day Fizzer stable + new engineer onboarding drill passes.

### 9.2 Final substrate (authoritative)

```
INGEST     → RawIngestionRecord
MATERIALIZE→ CortexCanonicalTransformMaterialization + CortexCanonicalIdentityAnchor
REPAIR     → org entities + candidates (paginated, lease cursor)
PROMOTE    → authoritative org links (fair rules, capped pass)
EXPORT     → OrgGraphProjectionV1 stable hash (ephemeral)
```

**Five verbs. Five owners. One worker queue for substrate.**

### 9.3 Final ownership map

| Verb | Owner function | State |
|------|----------------|-------|
| Ingest | `execute_connector_sync` | connector checkpoints |
| Dirty | `mark_dirty_and_enqueue_convergence_v1` | lease obligation |
| Materialize | `drain_forward_progress_backlog` | deferrals |
| Repair | `run_identity_substrate_repair_slice_v1` | lease repair cursor |
| Promote | `run_graph_density_promotion_pass_v1` | auth links |
| Export | `run_graph_projection_export_for_pipeline_v1` | phase 04 hash |
| Truth | `build_substrate_truth_v1` | read-only aggregate |

### 9.4 Final operator model

| Action | Effect |
|--------|--------|
| View Substrate | `GET /cortex/substrate/truth` |
| Repair | Reset cursor + mark dirty |
| Ingest now | `trigger-sync` (connector) |
| Inspect person | People cluster view |
| Debug | Gated `/cortex/debug/*` (replay export, force promotion) |

**No** “rebuild continuity”, “flush to identity”, “replay job”, “backfill anchors” on primary nav.

### 9.5 Final deploy / validation model

| When | What |
|------|------|
| CI | M9 + residue grep + `substrate_truth_v1` schema + phase receipt schema |
| Pre-deploy | Unit + substrate integration (ingest→slice mocked) |
| Post-deploy | ECS SHA + snapshot diff + V4–V7 motion |
| Weekly | Fizzer baseline commit if improved |
| On-call | Only `substrate_truth_v1` + `continuity_audit_snapshot.py` |

### 9.6 Final module shape (recommended)

**KEEP (substrate core package):**

```
domains/cortex/
  ingestion/          # sync_router, scheduler, post_ingestion → dispatch only
  canonical/          # transform_runtime, forward_progress, identity_runtime
  identity/           # repair_v1, backfill, anchor_continuity, promotion writer, projection_export
  execution/          # lease, dual_lane, convergence_dispatch, enqueue
  substrate_pipeline/ # phase_runners (02–04 only for substrate doc), truth builder
  contracts/          # substrate_v1.yaml
```

**MOVE out of hot path (subpackage or mark downstream):**

```
operational_runtime/  # CESP, synthesis scheduling, traversal scheduling — not substrate
unlock/               # delete or archive entire package
substrate_pipeline/continuity_p0_*  # delete (CI extracts to tests only)
pipeline/continuity_overview_v1     # demote to downstream dashboard
```

**DELETE packages (post-purge):**

```
domains/cortex/unlock/               # wedge era
scripts/archive/continuity_proofs/   # optional git delete
graph_hash_autonomous_chain.py
pipeline_continuation.py             # table + module when reads gone
```

Target: **&lt;40 Python modules** in the substrate critical path (ingest + canonical + identity + execution slice + truth).

### 9.7 Final invariant laws (enforced in CI)

| Law | Enforcement |
|-----|-------------|
| L1–L9 from §9.2 | grep + integration tests |
| L10 | No import from `unlock` in `execution` or `identity` |
| L11 | No `cortex_org_links` INSERT outside `authoritative_writer` + tests |
| L12 | Admin routes mutate state only via debug namespace except revoke link |
| L13 | `substrate_truth_v1` schema version bumped on breaking changes |

### 9.8 Wave 9 exit criteria — domain purge complete

1. New engineer explains substrate in **&lt;2 minutes** (recorded onboarding drill).
2. Substrate-critical module list **≤40** files.
3. `domains/cortex/identity/` contains **no** replay runtime in non-debug path.
4. One OpenAPI contract for substrate truth.
5. Repo grep for `identity_continuity_rebuild` = debug/tests only.
6. Cortex domain feels **boring** — audit confirms no new parallel paths for 30 days.

---

## 13. Full roadmap summary (Waves 0–9)

| Wave | Name | Delivers |
|------|------|----------|
| **0** | Substrate truth | One observable state |
| **1** | Promotion + phase honesty | Stop fake motion |
| **2** | Rebuild collapse | One repair semantics |
| **3** | Dead Celery/runtime | Fewer ghosts |
| **4** | Graph truth + People | Honest KPIs |
| **5** | Deploy validation | Trustworthy ship |
| **6** | Domain residue purge | Tree matches runtime |
| **7** | Contract collapse | One shape per concept |
| **8** | Operational simplicity | Predictable mutations |
| **9** | Final domain shape | Boring Cortex |

**Dependency:** 0→1→2→3→4→5 **must** complete before **6**. 6→7→8→9 sequential recommended; 7 and 8 can overlap if contract freeze is explicit.

---

## 14. Success criteria — full program (Waves 0–9)

| Stage | Done when |
|-------|-----------|
| **Coherence (0–5)** | Fizzer V6–V8; no duplicate promotion; truth primary |
| **Purge (6)** | Residue grep gates; debug quarantined |
| **Contracts (7)** | `substrate_truth_v1` only on Overview |
| **Simplicity (8)** | Runbook ≤3 pages; all mutators documented |
| **Final (9)** | &lt;2 min explain; ≤40 substrate modules; 30-day no drift |

**Anti-goal:** Preserving code because it “might be useful later.”  
**Goal:** Small, clear, coherent, deterministic, repairable, truthful, operationally boring.

---

## Related documents

- Investigation: [`cortex_minimal_substrate_reality_audit_v1.md`](cortex_minimal_substrate_reality_audit_v1.md)
- Identity deep dive: [`cortex_identity_reconstruction_full_system_audit_v1.md`](cortex_identity_reconstruction_full_system_audit_v1.md)

---

*End of substrate collapse plan v1 — plan only, no code.*
