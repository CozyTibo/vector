# Cortex Simplification & Determinism Refactor

**Status:** Authoritative architecture reduction plan  
**Supersedes:** Exploratory orchestration paths documented in the Deep Cortex Execution Audit  
**Goal:** One tenant-scoped execution FSM. Subtraction over sophistication.

---

## Executive mandate

Cortex is being refactored for **deterministic execution**, not feature completeness. The bottleneck is **trustworthiness of the substrate**, not intelligence layers (identity, graph, retrieval, synthesis).

**Core realization:** We built a *distributed autonomous recovery substrate* before proving a *deterministic tenant execution pipeline*. This refactor corrects that by **deleting competing execution authorities**, not adding more retries, watchdogs, doctrine, or sidecars.

**Authoritative decisions (non-negotiable):**

1. Convergence runtime is the **only** substrate runtime.
2. Legacy Celery phase chaining **dies** (no blind `chain_after_phase_v1`).
3. Shadow orchestration (**progression, watchdog continuation ownership, duplicate resume paths**) **dies**.
4. Admin **never** bypasses execution contracts.
5. Replay = **delete downstream derived state + rerun deterministic transform** (one contract).
6. Sidecar orchestration **collapses** into phases or is removed.

---

## 1. Authoritative execution owner map

### 1.1 Current orchestration authorities

| Owner | Location | Trigger | Responsibilities | Continuation | Retry | Replay | Downstream schedule |
|-------|----------|---------|------------------|--------------|-------|--------|---------------------|
| **A. Convergence worker** | `convergence/run_convergence.py`, `lease.py`, `enqueue.py`, `sweep.py` | Post-ingest dirty mark, sweeper beat, self-requeue, TCRE resume | Inline phases 02–08 under lease; canonical gate before identity; `phase_cursor` | Lease `WAITING` + `phase_cursor` | Convergence retry schedule, topology cooldown, time budget requeue | Uses forward-progress drain (not replay jobs) | None (inline only) |
| **B. Legacy substrate coordinator** | `orchestrator.schedule_substrate_pipeline_v1`, `cortex_substrate_pipeline.coordinator` | Flag-off post-ingest, flush-rerun (partial) | Create pipeline run; enqueue phase 02 | Delegates to Celery chain | Debounce revoke/coalesce | N/A | `enqueue_next_pipeline_phase_v1` |
| **C. Legacy Celery phase chain** | `cortex_substrate_pipeline.phase`, `chain_after_phase_v1` | After each phase 02–05 completes | Run one phase; **blind chain** to next | Phase 06 stops chain; 07 uses synthesis hook | Celery `max_retries=3` on phase task | N/A | Enqueues next phase task |
| **D. Pipeline continuation** | `pipeline_continuation.py` | TCRE complete, traversal wait | `WAITING` / `RESUMED` rows, resume receipts | **Owns** TCRE/traversal gaps (legacy path) | Stale detection | Resume idempotency nonces | `resume_pipeline_after_tcre_completion_v1` → phase 07 |
| **E. Convergence TCRE resume** | `convergence/tcre_resume.py` | TCRE job complete (convergence on) | Sets lease cursor to phase 07 | **Parallel** to D when flag on | Re-enqueue convergence | N/A | Inline phase 07 in worker |
| **F. Substrate operational progression** | `substrate_operational_progression.py`, beat tick | Watchdog, TCRE complete, retrieval published, manual admin | **Shadow coordinator**: inline 06, re-enqueue 06/07, synthesis chain, retrieval retries | Reads continuation; may compete with D/E | `MAX_RETRIEVAL_MATERIALIZATION_RETRIES_V1=3` | Recovery receipts | `enqueue_next_pipeline_phase_v1` |
| **G. Continuity watchdog** | `stalled_pipeline_recovery.py`, `substrate_continuity_watchdog.py` | Beat (legacy), admin one-shot | Detect stall; `recover_stalled_pipeline_v1` | Re-enqueue phases / resume TCRE | Auto-recover flag | N/A | Competes with F |
| **H. Post-ingestion dispatch fork** | `post_ingestion_refresh_dispatch.py` | After `execute_connector_sync` | Routes to A or B | N/A | N/A | N/A | **Splits runtime by flag** |
| **I. Ingestion scheduler** | `ingestion/scheduler.py`, beat tick | Periodic | Connector sync only | N/A | Min-gap | Replay sync on `cortex_replay` queue | → H |
| **J. Standalone canonical backlog task** | `cortex_canonical_materialize_backlog.py` | Admin async, optional | `drain_stub_materialize_backlog` outside FSM | N/A | Task retries | N/A | **Bypasses phase gate** |
| **K. Flush-rerun orchestrator** | `cortex_full_pipeline_rerun.py` | Admin flush | Sync all connectors + start pipeline | Uses B/C path today | Per-connector | N/A | Mixed |
| **L. CESP sidecar schedulers** | `graph_density_promotion`, `substrate_traversal_scheduling`, `substrate_tcre_saturation_scheduling`, `substrate_synthesis_activation_scheduling`, traversal retry, stalled traversal, orphan stitch | Phase runners + admin schedule/run | Parallel Celery passes | Some set traversal continuation wait | Pass-local | Various replay contracts | **Hidden parallel graph** |
| **M. TCRE Celery job** | `cortex_tcre_reconstruction_jobs.py` | Phase 06, admin reconstruct | Execute job; **direct** incremental retrieval materialization | Callback to D/E/F | Job FSM | Replay twin/diff admin | Calls pipeline resume hooks |
| **N. Domain replay jobs** | `canonical/replay_runtime.py`, `identity/org_link_replay_runtime.py`, ingestion replay lane | Admin replay endpoints | Separate job universes | Per-job checkpoints | Resume failed jobs | **Separate orchestration** | May mutate state off-FSM |
| **O. Admin one-shots** | `admin.py`, `admin_substrate_pipeline.py`, `admin_cortex_operational_runtime.py` | Operator | Materialize, backlog drain, rebuild identity, recover stalled, progression continue | Force semantics | N/A | Multiple paths | **Contract bypass** |

### 1.2 Classification: KEEP / MERGE / DELETE

| Owner | Verdict | Becomes |
|-------|---------|---------|
| **A. Convergence worker** | **KEEP** (evolve) | Sole **Tenant Execution Engine** |
| **B. Legacy coordinator** | **DELETE** | Fold `start_substrate_pipeline_run` into FSM persistence only |
| **C. Celery phase chain** | **DELETE** | Replace with single `run_tenant_execution_slice` task (re-enqueue self) |
| **D. Pipeline continuation** | **MERGE** | Subsumed into FSM `AWAITING_*` states + transition log |
| **E. Convergence TCRE resume** | **MERGE** | One `on_async_job_complete` handler on FSM |
| **F. Operational progression** | **DELETE** | Recovery = `rerun_phase(from=X)` only |
| **G. Watchdog (as orchestrator)** | **DELETE** | Stall → mark FSM `STALLED` + metric; optional admin rerun |
| **H. Post-ingest fork** | **DELETE** (**M2–M4 done**) | Always dirty-mark + enqueue execution engine |
| **I. Ingestion scheduler** | **KEEP** | Triggers `INGESTING` only; no substrate phases |
| **J. Standalone backlog task** | **DELETE** | Canonical only via `CANONICAL_DRAINING` phase |
| **K. Flush-rerun** | **MERGE** | Admin: `clear_outputs(from=phase)` + `enqueue_rerun(from=phase)` |
| **L. CESP sidecars** | **DELETE / INLINE** | Required work → phase body; optional → removed |
| **M. TCRE job** | **KEEP** (narrow) | Async step inside `AWAITING_TCRE`; completion = FSM event only |
| **N. Domain replay jobs** | **DELETE** (orchestration) | Keep transform functions; drop job FSMs |
| **O. Admin one-shots** | **DELETE** (execution semantics) | Replace with restart/clear/enqueue/inspect |

### 1.3 Target: ONE execution owner

**`TenantExecutionEngine`** (evolved from convergence + slimmed substrate pipeline):

- **One** Postgres row per tenant: execution state (FSM), cursor, obligation epoch, lease holder, transition log pointer.
- **One** Celery task: `vector.cortex.execution.run_slice` (re-enqueues itself; no per-phase task IDs).
- **One** continuation model: FSM states `AWAITING_TCRE`, `AWAITING_TRAVERSAL` (if kept).
- **One** replay contract: `clear_derived_state(from_phase)` + `cursor = from_phase`.
- **One** beat: convergence sweeper (renamed execution sweeper) + ingestion scheduler only.

---

## 2. Execution path collapse plan

### 2.1 Target flow

```
trigger (ingest complete | admin rerun | sweeper)
  → mark tenant execution DIRTY (bump epoch)
  → enqueue run_execution_slice (no stable task id revoke games)
  → acquire lease
  → read FSM state + cursor
  → run exactly one phase slice OR handle async completion event
  → validate gate → advance cursor OR stay OR mark BLOCKED
  → persist transition log
  → release lease; re-enqueue if DIRTY or slice incomplete
```

### 2.2 Migration order (minimize production risk)

| Step | Action | Risk | Mitigation |
|------|--------|------|------------|
| **M0** | Feature telemetry: log `execution_path=convergence\|legacy\|progression\|admin_bypass` per tenant run | Low | **Done** — `execution/execution_path_telemetry.py`, structured log `cortex_execution_path` |
| **M1** | **P0 determinism fix:** In `run_cortex_substrate_pipeline_phase_task`, do not call `chain_after_phase_v1` after phase 02 if phase status is `waiting` or `failed` with zero successes | Medium | **Done** — `canonical_phase_gate.py`; flag `CORTEX_SUBSTRATE_PIPELINE_CANONICAL_CHAIN_GATE_ENABLED` (default true) |
| **M2** | Force `cortex_convergence_runtime_enabled=true` everywhere; remove flag branch in `post_ingestion_refresh_dispatch` | Low | **Done** — convergence-only dispatch; removed `cortex_convergence_runtime_enabled` setting; TCRE resume via convergence only |
| **M3** | Disable legacy beat: `cortex_convergence_disable_legacy_progression_beat=true` (already default); delete watchdog/progression beat entries | Low | **Done** — beat = ingestion + convergence sweep only; removed `cortex_convergence_disable_legacy_progression_beat`; `verify_legacy_substrate_beats_absent_from_celery_beat_v1` |
| **M4** | Stop enqueueing `run_cortex_substrate_pipeline_coordinator_task` from all callers; redirect to `enqueue_tenant_convergence_v1` | Medium | **Done** — `schedule_substrate_pipeline_v1` + legacy post-ingestion Celery task → dirty mark + convergence; coordinator deprecated (admin-only); `verify_schedule_substrate_pipeline_uses_convergence_v1` |
| **M5** | Rename convergence → `execution` package; add FSM table or extend `CortexTenantConvergenceLease` with explicit `fsm_state` | Medium | **Done** — `execution/` package; lease `fsm_state` + `block_*`; `cortex_execution_transition_log`; `CortexTenantExecution` alias; `convergence/` re-export shims |
| **M6** | Replace per-phase Celery tasks with single slice task; delete `chain_after_phase_v1` | High | **Done** — `vector.cortex.execution.run_slice`; `enqueue_execution_slice_at_phase_v1`; removed `chain_after_phase_v1`; legacy phase/coordinator tasks deprecated (no chain) |
| **M7** | Delete `substrate_operational_progression.py` and callers; migrate retrieval retry to FSM `BLOCKED` + manual/admin rerun | High | **Done** — deleted coordinator + Celery tick task; `execution/progression_status.py`, `blocked.py`, `admin_rerun.py`; retrieval policy in `run_tenant_execution_v1`; admin `POST …/progression/continue` → `admin_rerun_substrate_execution_v1`; [operator playbook](#m7-operator-playbook) |
| **M8** | Collapse admin execution endpoints (section 5) | Medium | Deprecation period with 410 + replacement routes |
| **M9** | Delete dead modules (section 9) | Low after M6–M8 | CI grep for imports |

### 2.3 Temporary compatibility (short-lived only)

- **Do not** maintain long-term dual paths.
- At M1–M4: legacy coordinator may remain **callable from admin only** with loud deprecation warning, max 2 weeks.
- No new compatibility shims.

### 2.4 Feature flags to remove (after migration)

| Flag | Action |
|------|--------|
| `cortex_convergence_runtime_enabled` | Remove (always on) |
| `cortex_convergence_disable_legacy_progression_beat` | **Removed (M3)** |
| `cortex_substrate_continuity_watchdog_auto_recover_enabled` | Remove (no auto-orchestration recovery) |
| `cortex_substrate_operational_progression_tick_*` | **Removed (M7)** |
| Debounce/coalesce settings for legacy coordinator | Remove |
| `cortex_substrate_pipeline_max_concurrent_per_tenant` | Replace with single lease (already 1 writer) |

### 2.5 Dead paths to delete (explicit)

- `schedule_substrate_pipeline_v1` debounce + revoke stable task id
- `run_cortex_substrate_pipeline_phase_task` (all phases)
- `run_cortex_post_ingestion_substrate_refresh_task` alias
- `chain_after_phase_v1`, `enqueue_next_pipeline_phase_v1` (as chaining semantics)
- `continue_substrate_operational_progression_v1`
- `run_stalled_pipeline_watchdog_v1` as **orchestrator** (keep stall **detection** as read-only alert)
- `recover_stalled_pipeline_v1` re-enqueue logic → admin `rerun_from_phase`
- Standalone `drain_stub_materialize_backlog_task` admin path
- All `app/tasks/cortex_substrate_*` sidecar tasks (section 6)

### 2.6 Rollout risks

| Risk | Mitigation |
|------|------------|
| Tenants mid-flight on legacy Celery chain | M1 gate fix immediately; M4 drain pending coordinator tasks |
| TCRE jobs in flight without pipeline scope | Completion handler must read FSM not continuation table |
| Admin scripts using materialize/backlog | Publish migration guide before M8 |
| Long canonical topology_wait | FSM `BLOCKED` with reason; no fake advance to identity |
| Test suite tied to PIPE-085 progression laws | Delete or rewrite tests that assert shadow orchestration |

### M7 operator playbook

When a tenant is stuck after ingest with **retrieval operational starvation** (upstream TCRE/walks/org-link work exists but published index has zero rows):

1. **Inspect** `GET /admin/tenants/{tenant_id}/cortex/substrate-pipeline/progression-status` — check `execution_lease.fsm_state`, `block_reason_code`, `phase_status`, and `retrieval_index_row_count`.
2. **If `fsm_state` is `BLOCKED`** with `retrieval_retry_exhausted`: fix upstream data (TCRE completion, walks, org links), then **`POST …/progression/continue`** (optional `force=true`) — clears block, marks dirty, enqueues `vector.cortex.execution.run_slice` at the first incomplete phase (or current cursor).
3. **Do not** invoke removed Celery task `vector.cortex.operational_runtime.substrate_progression_tick`; convergence sweeper + execution slice are authoritative.
4. **Bounded retries** (`MAX_RETRIEVAL_MATERIALIZATION_RETRIES_V1=3`) run inside the execution slice only; further automatic re-enqueue stops at `BLOCKED`.

---

## 3. Phase contract rewrite

Each phase exposes **only** the following. No hidden recovery, no sidecar scheduling, no implicit downstream triggers.

### 3.1 INGESTING (connector sync)

| Field | Definition |
|-------|------------|
| **Inputs** | Connector credentials, checkpoint cursor, routing policy |
| **Deterministic transform** | Fetch → normalize → `RawIngestionRecord` upsert with idempotency key |
| **Outputs** | Raw rows, checkpoint, optional execution-reconstruction events |
| **Completion** | Sync finished without fatal error (per connector contract) |
| **Blocked** | Policy off, auth failure, unrecoverable connector error |

### 3.2 CANONICAL_DRAINING

| Field | Definition |
|-------|------------|
| **Inputs** | Raw rows without materialization for bundle; topology deferral state |
| **Deterministic transform** | `drain_forward_progress_backlog` (fair passes) + determinism repair scan |
| **Outputs** | `CortexCanonicalTransformMaterialization`, anchors, deferral updates |
| **Completion** | `_untreated_raw_exists == false` AND no active topology_wait with zero progress in this slice OR explicit `BLOCKED` with reason |
| **Blocked** | `topology_wait` with 0 successes and parents not ingestible; permanent orphan; trust-state forbid |

**Gate to next phase:** `may_advance_identity = completion` (not phase row `completed` with empty work).

### 3.3 IDENTITY

| Field | Definition |
|-------|------------|
| **Inputs** | `CortexCanonicalIdentityAnchor` rows |
| **Deterministic transform** | Anchor backfill → org handles → link candidate generation |
| **Outputs** | `CortexOrgEntity`, candidates, audit receipt |
| **Completion** | Transform finished (handles may still be 0 if no anchors—report as `completed_empty`, not fake success) |
| **Blocked** | Canonical gate failed (must not run) |

### 3.4 GRAPH

| Field | Definition |
|-------|------------|
| **Inputs** | Org links, identity handles |
| **Deterministic transform** | `graph_projection_export` (org link replay job kind) |
| **Outputs** | Projection stable hash, verification slice |
| **Completion** | Export job terminal success |
| **Blocked** | Identity prerequisite missing (optional strict mode) |

**Sidecar removal:** graph density promotion becomes optional post-export hook **inside** same slice or deleted.

### 3.5 TRAVERSAL

| Field | Definition |
|-------|------------|
| **Inputs** | Graph projection hash, org graph slice |
| **Deterministic transform** | Substrate traversal materialization + **required** OCTS walk scheduling inline (if kept) |
| **Outputs** | Traversal artifacts, walk job IDs |
| **Completion** | Materialization succeeded; walks enqueued or completed per contract |
| **Blocked** | Graph disconnected (if strict)—FSM `BLOCKED`, not silent schedule skip |

**Sidecar removal:** separate `schedule_octs_walks_for_tenant` Celery task deleted; work runs in phase slice.

### 3.6 AWAITING_TCRE

| Field | Definition |
|-------|------------|
| **Inputs** | Traversal/TCRE eligibility scope |
| **Deterministic transform** | Enqueue **one** reconstruction job bound to `execution_run_id` |
| **Outputs** | `CortexTcreReconstructionJob` id |
| **Completion** | Job status terminal success |
| **Blocked** | Upstream canonical backlog (must not enqueue) |

**FSM:** Enter `AWAITING_TCRE` after enqueue; exit on job callback only.

**Remove:** TCRE saturation pass, incremental retrieval in job callback (move to RETRIEVAL phase only).

### 3.7 RETRIEVAL

| Field | Definition |
|-------|------------|
| **Inputs** | TCRE artifacts, walks, org links |
| **Deterministic transform** | `materialize_retrieval_index_for_pipeline` |
| **Outputs** | Published index epoch, entries |
| **Completion** | `entries_materialized > 0` OR explicit `healthy_idle` (no upstream candidates) |
| **Blocked** | `operational_starvation` upstream → FSM `BLOCKED`, not phase `completed` |

**Remove:** synthesis activation scheduling as separate orchestrator; phase 08 follows gate.

### 3.8 SYNTHESIS

| Field | Definition |
|-------|------------|
| **Inputs** | Published retrieval epoch, eligible scopes |
| **Deterministic transform** | Synthesis job envelope execution for eligible scopes |
| **Outputs** | Synthesis artifacts |
| **Completion** | All eligible scopes terminal or none eligible (`healthy_idle`) |
| **Blocked** | Retrieval gate failed; forbidden backoff |

### 3.9 IDLE

Tenant execution quiescent; `obligation_epoch` caught up to `completed_epoch`.

### 3.10 Removed concepts (per phase)

- `wait_phase_v1` without blocking FSM advance (legacy Celery allowed chain anyway)
- Phase-local Celery `schedule_*` calls
- `continue_substrate_operational_progression` retrieval retries
- Completeness propagation as execution gate (keep as **read-only diagnostics** only)

---

## 4. Replay reduction plan

### 4.1 One replay contract

```text
replay(tenant_id, from_phase, scope?) :=
  1. assert no execution lease held (or force with admin break-glass)
  2. clear_derived_state(tenant_id, from_phase, scope)
  3. set execution.cursor = from_phase
  4. mark DIRTY; enqueue run_execution_slice
```

**`clear_derived_state` matrix (deterministic deletes):**

| From phase | Clear (derived only; raw ingest preserved unless scoped) |
|------------|----------------------------------------------------------|
| CANONICAL | Materializations, anchors, deferrals, canonical failures (scoped) |
| IDENTITY | Org entities, candidates, identity audits (not raw/canonical) |
| GRAPH | Graph projection exports (not identity) |
| TRAVERSAL | Traversal artifacts, walk jobs |
| TCRE | Reconstruction jobs + objects |
| RETRIEVAL | Index epochs, entries |
| SYNTHESIS | Synthesis jobs + artifacts |

### 4.2 Eliminate (orchestration layer)

| Current | Action |
|---------|--------|
| `canonical/replay_runtime.py` job FSM + resume | Keep `execute_canonical_replay_job` logic as **batch transform** invoked only from `replay(from=CANONICAL)` |
| `canonical/replay_topology.py` stage barriers as continuation | Use same topology engine as forward drain; no separate checkpoint universe |
| Ingestion `cortex_replay` queue as substrate runtime | Keep for **re-fetch raw** only; triggers INGESTING, not parallel substrate |
| Org link replay jobs admin | `replay(from=GRAPH)` |
| TCRE replay twin / replay diff admin | Inspect-only; not execution paths |
| `substrate_replay_storm_handling`, `cesp_replay_storm_gate` | Delete (doctrine) |
| 26 `*replay*` modules | Retain **pure functions** for equivalence proofs in tests; drop scheduling |

### 4.3 Replay ≠ recovery

- Recovery is **`replay(from=blocked_phase)`**, not watchdog/progression.
- No `resume_canonical_replay_job` as special case—rerun slice from cursor.

### 4.4 Idempotency

- Replay identity: `(tenant_id, from_phase, scope_digest, obligation_epoch)`.
- All transforms remain delete-then-insert at natural keys (already mostly true for canonical).

---

## 5. Admin simplification plan

### 5.1 New admin surface (only)

| Operation | API shape | Behavior |
|-----------|-----------|----------|
| **Inspect** | GET state, completeness, transition log | Read-only |
| **Restart from phase** | POST `execution/restart?from_phase=` | Set cursor, mark dirty, enqueue slice |
| **Clear outputs** | POST `execution/clear?from_phase=&scope=` | Derived deletes per replay matrix |
| **Enqueue rerun** | POST `execution/rerun` = clear + restart | Atomic |
| **Trigger ingest** | POST `ingestion/sync` | INGESTING only |

### 5.2 Admin actions audit

| Endpoint / action | Bypasses contract? | Unsafe mutation? | Alternate semantics? | Verdict |
|-------------------|-------------------|------------------|----------------------|---------|
| `canonical/transform/materialize` (single row) | **Yes** — skips topology order | Yes | Direct write | **DELETE** → rerun canonical slice |
| `canonical/transform/materialize-backlog` (sync) | **Yes** | Yes | Parallel drain | **DELETE** |
| `canonical/transform/materialize-backlog-async` | **Yes** | Yes | Task J | **DELETE** |
| `canonical/replay-job/run`, `resume` | **Yes** | Yes | Replay universe N | **DELETE** → `execution/rerun` |
| `canonical/verification/repair-determinism-drift` | Partial | Yes | Keep as **repair transform** inside canonical phase only, invoked by engine | **MERGE** |
| `identity/rebuild-continuity` | **Yes** | Yes | Parallel identity path | **DELETE** → `rerun from=IDENTITY` |
| `identity/link-candidates/regenerate-async` | **Yes** | Yes | Side job | **DELETE** |
| `identity/authoritative-replay-async` | **Yes** | Yes | Replay universe | **DELETE** |
| `identity/org-link-replay-job/*` | **Yes** | Yes | Graph replay | **DELETE** → `rerun from=GRAPH` |
| `ingestion/trigger-sync` | No (ingest only) | No | OK | **KEEP** |
| `ingestion/trigger-replay` | No if only re-ingest | No | OK | **KEEP** (ingest lane) |
| `flush-rerun-to-identity` | **Yes** | **Destructive** | Flush + B/C path | **REPLACE** → `clear from=CANONICAL` + ingest all + `rerun` |
| `reasoning/runtime/reconstruct` | **Yes** | Yes | Skips FSM | **DELETE** → only via AWAITING_TCRE |
| `reasoning/runtime/replay-twin`, `replay-diff` | No (read/compare) | No | Inspect | **KEEP** (read-only) |
| `substrate-pipeline/stalled/.../recover` | **Yes** | Yes | Watchdog G | **DELETE** → `restart from=cursor` |
| `substrate-pipeline/continuity-watchdog/run` | **Yes** | Yes | Watchdog | **DELETE** (read-only stall report optional) |
| `substrate-pipeline/continue-progression` | **Yes** | Yes | Progression F | **DELETE** |
| Operational runtime `.../schedule`, `.../run` (density, walks, retry, saturation, synthesis activation) | **Yes** | Yes | Sidecars L | **DELETE** |
| `retrieval/index/rebuild`, `bootstrap` | **Yes** | Yes | Bypass RETRIEVAL | **REPLACE** → `rerun from=RETRIEVAL` |
| `synthesis/job/run`, `resynthesize` | **Yes** | Yes | Bypass SYNTHESIS gate | **REPLACE** → `rerun from=SYNTHESIS` |
| `memory/recovery/validate` | Partial | Can repair raw | Special | **FREEZE** then narrow to raw-only repairs |
| Catalog GET endpoints | No | No | Read | **KEEP** |

### 5.3 Admin principle

> Admin never runs transforms. Admin only **commands the execution engine** and **inspects state**.

---

## 6. Sidecar collapse plan

| Sidecar | Trigger today | Required? | Decision |
|---------|---------------|-----------|----------|
| **Graph density promotion** | After phase 04 + admin | No for substrate truth | **REMOVE** (defer product maturity) |
| **OCTS walk scheduling** | After phase 05 + admin | **Yes** for traversal truth | **INLINE** into TRAVERSAL phase slice |
| **TCRE saturation** | After phase 06 + admin | No | **REMOVE** |
| **Synthesis activation scheduling** | After phase 07 + admin | **Yes** for phase 08 entry | **INLINE** into RETRIEVAL exit gate (enqueue synthesis jobs in same slice, not separate Celery) |
| **Traversal retry + heal** | Admin / beat | No | **REMOVE** → `rerun from=TRAVERSAL` |
| **Stalled traversal recovery** | Admin / beat | No | **REMOVE** |
| **Orphan continuity stitch** | Admin | No | **REMOVE** |
| **Graph orphan continuity** | Coupled to density | No | **REMOVE** |
| **Completeness propagation gating** | Read by schedulers | Observability only | **KEEP** read-only; remove gating calls |
| **Fake-green / starvation classifiers** | Observability | **KEEP** as diagnostics tied to FSM `BLOCKED` reasons |
| **CESP doctrine gates** (`cesp_*_gate.py`) | CI/law tests | Not runtime | **FREEZE** in tests; no runtime imports in engine |

### 6.1 Celery tasks to delete (sidecar)

- `cortex_graph_density_promotion.py`
- `cortex_substrate_traversal_scheduling.py` (as separate task—logic inlined)
- `cortex_substrate_traversal_retry.py`
- `cortex_substrate_stalled_traversal_recovery.py`
- `cortex_orphan_continuity_stitch.py`
- `cortex_substrate_tcre_saturation_scheduling.py`
- `cortex_substrate_synthesis_activation_scheduling.py`

### 6.2 Phase runner cleanup

Remove from `phase_runners.py` all `schedule_*` / `run_*_after_phase*` imports and calls.

---

## 7. State machine reconstruction

### 7.1 States

| State | Meaning |
|-------|---------|
| `IDLE` | No pending obligation |
| `INGESTING` | Connector sync in progress (optional sub-state of engine or separate) |
| `CANONICAL_DRAINING` | Running canonical slice |
| `IDENTITY` | Identity slice |
| `GRAPH` | Graph slice |
| `TRAVERSAL` | Traversal slice |
| `AWAITING_TCRE` | TCRE job enqueued, not terminal |
| `RETRIEVAL` | Retrieval slice |
| `SYNTHESIS` | Synthesis slice |
| `BLOCKED` | Cannot advance without operator or upstream ingest fix |
| `STALLED` | Lease heartbeat timeout (inspect only) |

### 7.2 Transitions (authoritative)

```text
IDLE → INGESTING          [ingest triggered]
INGESTING → IDLE          [ingest done, no substrate obligation]
INGESTING → CANONICAL_DRAINING [ingest done, mark dirty]

CANONICAL_DRAINING → CANONICAL_DRAINING [slice incomplete, more raw]
CANONICAL_DRAINING → BLOCKED            [topology/block, 0 progress]
CANONICAL_DRAINING → IDENTITY           [gate: no untreated raw]

IDENTITY → GRAPH          [identity slice complete]
GRAPH → TRAVERSAL
TRAVERSAL → AWAITING_TCRE [job enqueued]
AWAITING_TCRE → RETRIEVAL [job succeeded]
AWAITING_TCRE → BLOCKED   [job failed]

RETRIEVAL → SYNTHESIS     [retrieval gate passed]
SYNTHESIS → IDLE          [synthesis complete, epochs aligned]

ANY → BLOCKED             [explicit block condition]
BLOCKED → *               [admin rerun from phase only]

STALLED → BLOCKED         [manual only]
```

### 7.3 Ownership

- **Single writer:** execution lease on `CortexTenantExecution` (rename from convergence lease).
- **Cursor:** `phase_cursor` + `fsm_state` redundant → keep one `cursor_phase` enum.

### 7.4 Blocking semantics

- `BLOCKED` persists `block_reason_code` + `block_detail` (e.g. `topology_wait`, `canonical_backlog`, `retrieval_starvation`).
- Phase DB rows mirror FSM for audit but **do not drive** transitions.

### 7.5 Retry semantics

- **No autonomous multi-owner retries.**
- Engine re-enqueues self when: slice incomplete within budget, `DIRTY` epoch bump, or async job pending.
- Topology wait: exponential backoff on **same cursor** (canonical), never advance.

### 7.6 Persistence model

| Store | Purpose |
|-------|---------|
| `CortexTenantExecution` | FSM state, cursor, epochs, lease, heartbeat |
| `CortexExecutionTransitionLog` | Append-only: `(at, from, to, trigger, receipt_hash, detail_json)` |
| `CortexSubstratePipelineRun` / `PhaseRun` | Optional audit mirror (can collapse to execution run later) |
| **Delete** `CortexPipelineContinuationState` | Replace with FSM `AWAITING_*` |

### 7.7 Continuation semantics (simplified)

- **Only async gap:** TCRE job (traversal wait optional—prefer synchronous completion in TRAVERSAL slice).
- Completion handler: `on_tcre_job_terminal(job_id)` → validate scope matches execution run → transition `AWAITING_TCRE → RETRIEVAL`.
- Idempotency: job_id + terminal status processed once (keep nonce pattern).

### 7.8 State transition log (required)

Every slice ends with:

```json
{
  "tenant_id": "...",
  "execution_run_id": "...",
  "from_state": "CANONICAL_DRAINING",
  "to_state": "IDENTITY",
  "trigger": "slice_complete",
  "gate_result": "pass",
  "processed_count": 42,
  "receipt_hash": "sha256:..."
}
```

---

## 8. Determinism gap report (prioritized)

| # | Violation | Severity | Location | Fix |
|---|-----------|----------|----------|-----|
| 1 | Celery chains identity while canonical `waiting` | **P0 Critical** | `cortex_substrate_pipeline.py` + `chain_after_phase_v1` | M1 gate or delete chain |
| 2 | Two post-ingest runtimes (convergence vs legacy) | **P0** | `post_ingestion_refresh_dispatch.py` | M2–M4 single path |
| 3 | Progression re-enqueues phases independently | **P0** | ~~`substrate_operational_progression.py`~~ | **M7 done** — execution slice + admin rerun |
| 4 | TCRE callback + progression + continuation triple resume | **P0** | `orchestrator.on_tcre_job_completed_*` | Merge to FSM handler |
| 5 | Incremental retrieval in TCRE task (skips RETRIEVAL gate) | **P1 High** | `cortex_tcre_reconstruction_jobs.py` | Move to RETRIEVAL only |
| 6 | Phase `completed` with zero processed | **P1** | `phase_runners`, repository | `completed_empty` / `BLOCKED` |
| 7 | Admin materialize/backlog bypass topology | **P1** | `admin.py` | M8 delete endpoints |
| 8 | Standalone backlog Celery task | **P1** | `cortex_canonical_materialize_backlog.py` | Delete |
| 9 | Multiple replay job writers without tenant lock | **P1** | replay runtimes | Single replay contract + lease |
| 10 | Sidecars schedule parallel work | **P2** | operational_runtime schedulers | Section 6 |
| 11 | Degradation projection implied blocking | **P2** | completeness_degradation | Document read-only |
| 12 | Convergence time budget mid-phase partial commit | **P2** | `run_convergence_v1` | Slice boundaries atomic per phase |
| 13 | Coordinator debounce revoke race | **P2** | `schedule_substrate_pipeline_v1` | Delete |
| 14 | No global tenant execution lock during admin replay | **P2** | admin replay jobs | Lease required |
| 15 | `finalize_pipeline_if_complete` treats `waiting` as incomplete but phases may diverge | **P2** | `orchestrator.finalize_*` | FSM drives truth |
| 16 | Flush-rerun uses legacy pipeline | **P2** | `cortex_full_pipeline_rerun.py` | Use execution rerun |
| 17 | Dual beat schedulers (sweep + watchdog + progression) | **P3** | `celery_app.py` | One sweeper |
| 18 | PIPE-085 law tests assert shadow orchestration | **P3** | tests | Rewrite |

---

## 9. Mass deletion plan

### 9.1 Delete immediately (after M1–M4, low dependency)

| Category | Paths / modules |
|----------|-----------------|
| Legacy chain | `chain_after_phase_v1`, `enqueue_next_pipeline_phase_v1` usage in phase task |
| Post-ingest fork branch | Legacy branch in `post_ingestion_refresh_dispatch.py` |
| Beat tasks | `cortex_substrate_continuity_watchdog.py`, `cortex_substrate_operational_progression.py` (tasks) |
| Progression | `substrate_operational_progression.py` (~700 LOC) |
| Autonomous progression laws | `substrate_autonomous_progression.py` (runtime asserts) — keep tests frozen or delete |
| Standalone backlog task | `app/tasks/cortex_canonical_materialize_backlog.py` |
| Post-ingestion alias task | `app/tasks/cortex_post_ingestion_substrate_refresh.py` |
| Schedule debounce infra | `infrastructure/cortex_substrate_pipeline_schedule.py` (if only used by legacy) |

**Estimated LOC removed:** ~2,500–4,000 (first wave)

### 9.2 Delete after single slice task (M6)

| Category | Paths |
|----------|-------|
| Celery substrate pipeline | `app/tasks/cortex_substrate_pipeline.py` |
| Coordinator scheduling | `schedule_substrate_pipeline_v1` body in `orchestrator.py` |
| Continuation table usage | `pipeline_continuation.py` (after FSM migration) |
| Stalled recovery orchestration | `stalled_pipeline_recovery.py` recover enqueue paths |
| Sidecar tasks | 7 tasks listed in §6.1 |

**Estimated LOC removed:** ~5,000–8,000 (second wave)

### 9.3 Merge (keep transform, delete orchestration)

| Keep function | Delete wrapper |
|---------------|----------------|
| `drain_stub_materialize_backlog` | Admin/tasks bypass |
| `materialize_raw_record` | Admin single-row |
| `execute_org_link_replay_job` | Separate replay job admin |
| `run_phase_*_v1` bodies | Per-phase Celery wrappers |
| `run_tenant_convergence_v1` loop | Replace with FSM driver |

### 9.4 Freeze first (do not delete until replacement)

| Item | Reason |
|------|--------|
| `CortexSubstratePipelineRun` / phase runs | Admin UI + metrics depend |
| Completeness projections | Dashboards |
| Catalog GET admin routes | Operators |
| TCRE job model | Async gap still needed |
| Ingestion scheduler | Independent trigger |

### 9.5 Doctrinal overengineering (delete from runtime imports)

- `cesp_*_gate.py` (runtime enforcement, not CI)
- `substrate_replay_storm_handling.py`
- `substrate_autonomous_progression` law assertions in hot path
- Normative freeze hashes in execution path (keep docs only)

**Bias:** If a module both schedules work and documents law, **delete scheduling**, keep doc in `DOCS/`.

### 9.6 Test deletion estimate

- Tests asserting `chain_after_phase_v1`, progression tick, watchdog recovery, sidecar schedule hooks: **rewrite or delete** (~30–50 test files touching phase085 orchestration).

---

## 10. Final target architecture

### 10.1 Diagram

```text
                    ┌─────────────────────┐
                    │  Triggers           │
                    │  - ingest scheduler │
                    │  - ingest complete  │
                    │  - execution sweep  │
                    │  - admin rerun      │
                    └──────────┬──────────┘
                               │
                               v
                    ┌─────────────────────┐
                    │ TenantExecutionEngine│
                    │  (one lease/tenant)  │
                    └──────────┬──────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         v                     v                     v
   ┌───────────┐      ┌──────────────┐      ┌──────────────┐
   │ FSM state │      │ Phase slices │      │ Transition   │
   │ + cursor  │      │ (deterministic│      │ log          │
   │           │      │  transforms)  │      │ (append-only)│
   └───────────┘      └──────────────┘      └──────────────┘
                               │
                    ┌──────────┴──────────┐
                    v                     v
              ┌──────────┐         ┌─────────────┐
              │ TCRE job │         │ Postgres    │
              │ (only    │         │ derived     │
              │  async)  │         │ state       │
              └──────────┘         └─────────────┘
```

### 10.2 Package layout (target)

```text
vector/domains/cortex/execution/
  fsm.py                 # states, transitions, gates
  engine.py              # run_slice, lease, enqueue
  replay.py              # clear_derived_state + rerun
  transition_log.py
  phase_canonical.py     # slice impl (or keep phase_runners, no orchestration)
  phase_identity.py
  ...
vector/domains/cortex/ingestion/   # unchanged trigger surface
vector/domains/cortex/canonical/   # transforms only, no replay job FSM
vector/domains/cortex/identity/    # transforms only
...
app/tasks/
  cortex_execution.py      # ONE task: run_execution_slice
  cortex_ingestion_sync.py
  cortex_ingestion_scheduler.py
  cortex_convergence.py    # renamed → cortex_execution_sweep.py
  cortex_tcre_reconstruction_jobs.py  # narrow callback
```

### 10.3 What operators experience

1. Open tenant execution inspect → see **one FSM state**, cursor, last 20 transitions, block reason.
2. If blocked → **Rerun from phase X** (not 15 different rebuild buttons).
3. Logs correlate: `execution_run_id` + `transition receipt_hash` only.

### 10.4 What developers experience

- **Linear reasoning:** trigger → slice → gate → next state.
- **No “which orchestrator won?”** questions.
- **Replay** is boring: clear + rerun.
- Intelligence layers consume **known-good** substrate states.

### 10.5 Explicit non-goals (this refactor)

- Autonomous distributed recovery sophistication
- CESP parallel maturity passes
- Replay equivalence proof frameworks in production path
- Phase 09 products integration
- Multi-pipeline concurrency per tenant
- Theoretical horizontal scale of orchestration

### 10.6 Success criteria

| Metric | Target |
|--------|--------|
| Execution paths per tenant | **1** |
| Celery substrate task types | **2** (slice + sweep) + TCRE + ingest |
| Admin execution endpoints | **≤5** command types |
| Identity run with canonical `waiting` | **0** incidents |
| Time to answer “why stuck?” | <5 min via transition log |
| Lines of orchestration code | **-60%** from baseline |

---

## Appendix A — Implementation phases (recommended schedule)

| Week | Deliverable |
|------|-------------|
| W1 | M1 P0 gate fix + M2 force convergence + telemetry |
| W2 | **M4–M6 done** |
| W3 | **M7 done**; M8 admin deprecation |
| W4 | M9 sidecar deletion + replay contract |
| W5 | M8 admin deprecation |
| W6 | M9 sidecar deletion + replay contract |
| W7 | Test rewrite + oper playbook + remove flags |

---

## Appendix B — Reference: audit cross-links

This plan implements the prior audit findings:

- **Dual runtime:** convergence vs legacy → Section 2, Decision 1
- **Celery identity advance on canonical waiting:** Section 8 #1, M1
- **Shadow progression:** Section 1 F, Section 9
- **Admin bypass:** Section 5
- **Replay fragmentation:** Section 4
- **Sidecars:** Section 6
- **Identity at 0 root cause:** Canonical gate (Section 3.2) — not identity phase skip

---

*Document owner: Cortex substrate team. Treat as authoritative for all Cortex orchestration work until superseded by implementation completion sign-off.*
