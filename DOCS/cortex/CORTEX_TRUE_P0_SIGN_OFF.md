# Cortex TRUE P0 Sign-Off — Final Deterministic Substrate Consolidation

**Status:** Authoritative implementation plan (post M0–M12 orchestration + per-phase reduction P0–P3)  
**Context:** [`CORTEX_SIMPLIFICATION_AND_DETERMINISM_REFACTOR.md`](./CORTEX_SIMPLIFICATION_AND_DETERMINISM_REFACTOR.md), [`CORTEX_PER_PHASE_SIMPLIFICATION_AUDIT.md`](./CORTEX_PER_PHASE_SIMPLIFICATION_AUDIT.md)  
**Date:** 2026-05-21  

---

## Executive mandate

Orchestration simplification is **largely complete**. The remaining highest-leverage work is **substrate truth formalization**, not another orchestration pass.

**This initiative is:**

- substrate truth formalization  
- deterministic execution sign-off  
- execution semantics stabilization  
- receipt standardization  
- state semantics unification  
- canonical simplification completion  
- legacy runtime burial  

**This initiative is NOT:**

- another orchestration cleanup  
- runtime sophistication  
- future-proof abstractions  

**Primary doctrine (repeat everywhere):**

```text
Does this increase execution truthfulness, or only sophistication?
If sophistication > truthfulness → delete.
```

**Target transform shape (every phase):**

```text
input → deterministic transform → explicit receipt → explicit outcome → explicit gate
```

---

## Current baseline (what is already true)

| Property | State | Evidence |
|----------|-------|----------|
| Single execution owner | **Mostly true** | `run_tenant_convergence_v1` in `execution/run_tenant_execution.py` drives phases 02–08 in-process |
| Post-ingest dispatch | **Single path (live)** | `ingestion/post_ingestion_refresh_dispatch.py` → `mark_tenant_dirty_v1` + `enqueue_tenant_convergence_v1` |
| Hot path boundaries | **CI-enforced** | `execution/scheduling.py` boundary verifiers + `verify_gp085_prog01` |
| CESP off hot path | **Done** | `verify_execution_hot_path_no_cesp_imports_boundary_v1` |
| Pass fairness on lease | **Removed** | Lease stores `last_canonical_outcome` / `convergence_health`, not `pass_index` |
| Continuation on hot path | **Removed** | Phase 06/08 + execution worker do not write `pipeline_continuation` |
| Phase runners thin | **Mostly** | `substrate_pipeline/phase_runners.py` (~285 LOC) delegates to domain transforms |

**Not signed off:** canonical internal fairness, duplicated observability, non-universal phase receipts, ambiguous stop semantics, dead runtime modules.

---

## Critical remaining gaps (priority order)

| # | Gap | Leverage | Risk if ignored |
|---|-----|----------|-----------------|
| 1 | Canonical still “smart” inside drain | **Highest** | Replay drift, operator confusion, hidden scheduler |
| 2 | Receipt semantics not universal | **High** | Debugging language fragmented |
| 3 | BLOCKED / stop semantics incomplete | **High** | Fake-green, weak replay |
| 4 | Execution observability duplicated | **Medium–High** | Stale mirrors, regression surface |
| 5 | Legacy runtime surfaces | **Medium** | Accidental resurrection |

---

# SECTION 1 — Canonical final simplification

## 1.1 Code map (audit surface)

| Component | Path | Role today |
|-----------|------|------------|
| Drain orchestrator | `canonical/forward_progress/drain_runtime.py` | Multi-batch slice loop, outcome classification, exports pass cooldown state **in drain output** (not lease) |
| Pass fairness | `canonical/forward_progress/pass_fairness.py` | Cooldowns, stall counts, `resolve_fair_pass_cursor` (skip cooled passes, deprioritize stalls) |
| Candidate selection | `canonical/forward_progress/candidate_selection.py` | Pass rotation + `list_forward_progress_candidate_ids` |
| Pass registry | `canonical/forward_progress/pass_registry.py` | `all_canonical_passes_fair_rotation()` ordering |
| Deferral store | `canonical/forward_progress/deferral_store.py` | Topology defer rows, release on parent materialize |
| Metrics / operator | `metrics.py`, `operator_snapshot.py` | Convergence health labels, admin panels |
| Materialize entry | `canonical/transform_runtime.py` → `materialize_stub_backlog` | Actual row transform + topology skip/defer |
| Phase entry | `substrate_pipeline/phase_runners.py` → `run_phase_02_canonical_v1` | Single `drain_forward_progress_backlog` call |
| Execution reaction | `execution/run_tenant_execution.py` | Reads `canonical_outcome`, topology cooldown requeue |

## 1.2 Inventory: remaining “smart runtime” inside canonical

| Behavior | Location | Determinism impact | Necessary? |
|----------|----------|-------------------|------------|
| **Pass rotation** | `resolve_fair_pass_cursor`, `pass_index` / `pass_index_next` in drain | Order of `(connector, resource_type)` pairs varies with stall history | **Deferrable** — only needed if strict FIFO across pairs is too slow; not needed for correctness |
| **Pass cooldown after topology-only batch** | `record_pass_topology_stall`, escalating seconds | Same backlog, different pass order on retry | **Questionable** — reduces spin; adds stateful ordering |
| **Stall-count deprioritization** | `resolve_fair_pass_cursor` candidate sort by stall count | Non-FIFO across passes | **Delete candidate** |
| **Full rotation topology stall detection** | `drain_runtime` lines ~196–234 | Emits `topology_wait` / `zero_progress_spin_detected` | **Keep simplified** — but surface via receipt, not scheduler semantics |
| **Deferral table** | `cortex_canonical_materialization_deferral` | Deterministic if release rules are deterministic | **Keep** — this is real topology truth, not fairness |
| **Permanent orphan promotion** | deferral `permanent_orphan` threshold | Bounded lifecycle | **Keep** — operator/admin visibility |
| **`convergence_health` heuristic label** | `_convergence_health_label` in drain | Operator UX only | **Admin-only** after sign-off |
| **Multi-batch slice cap** | `cortex_canonical_forward_progress_max_batches_per_slice` | Bounded work per execution slice | **Keep** — execution budget, not fairness |

**Verdict:** Canonical is still an **adaptive progression scheduler at the pass level**, even though the **lease no longer owns fairness state**. Fairness state now lives **inside each drain slice** (`pass_cooldown_until`, `pass_topology_stall_counts` in drain return JSON) and is re-derived each slice from empty dicts in `run_phase_02_canonical_v1` — meaning **rotation resets every slice** but **within-slice** behavior is still fair-pass sophisticated.

That hybrid is the worst of both worlds for mental models: operators think fairness was removed, but drain still rotates/skips/cools down passes.

## 1.3 Determinism & replay risks

| Risk | Mechanism | Symptom |
|------|-----------|---------|
| **Replay drift** | Pass order depends on cooldown/stall history | Same raw snapshot → different materialization order → different hashes |
| **Debugging ambiguity** | `canonical_outcome` vs phase row `waiting` vs FSM `CANONICAL_DRAINING` | “Why is tenant stuck?” requires 3 surfaces |
| **False topology_wait** | `full_rotation_topology_stall` with zero success | Execution requeues with cooldown — correct but opaque without receipt |
| **Slice cap vs backlog** | `hit_slice_cap` + `partial_progress` | Operator cannot tell “done” vs “budget exhausted” without reading JSON |

## 1.4 Target design: deterministic substrate compiler

```text
FIFO raw selection (stable sort keys)
  → topology defer (persisted, release on parent materialized)
  → deterministic materialize batch
  → explicit canonical receipt + outcome
```

### Invariants (canonical, post sign-off)

```text
C1. Candidate selection uses a total order on raw rows (e.g. connector, resource_type, source_key, id ASC).
C2. No pass cooldown / stall-count deprioritization on execution hot path.
C3. topology_wait is emitted only when deferral queue blocks all selected candidates.
C4. canonical_outcome is one of: progressed | partial_progress | topology_wait | idle | failed.
C5. Drain output includes receipt_hash over {bundle_id, batch_ids, outcome, counts, deferral_snapshot_id}.
C6. Deferral release is idempotent and keyed only on materialized parent facts.
```

### Deletion plan (canonical)

| Delete / gut | Replacement |
|--------------|-------------|
| `pass_fairness.py` cooldown/stall rotation on hot path | Fixed pass order from `pass_registry` OR single combined FIFO queue |
| `resolve_fair_pass_cursor` stall deprioritization | `resolve_next_pass_fixed_order(pass_index)` modulo N |
| `convergence_health` on hot path output | Move to `operator_snapshot` / admin only |
| Escalating cooldown multipliers | Single topology cooldown constant (execution already has `cortex_canonical_topology_wait_cooldown_seconds`) |

### Keep (canonical)

- `deferral_store.py` + deferral table (topology truth)  
- `release_deferrals_with_materialized_parents`  
- `materialize_stub_backlog` core transform  
- Multi-batch **slice budget** (execution concern, not fairness)  
- `CANONICAL_OUTCOME_*` enum  

### Rollout safety (canonical)

| Step | Action | Rollback |
|------|--------|----------|
| C-A | Add `drain_forward_progress_backlog_deterministic_v1` behind flag; shadow-compare hashes in CI | Flag off |
| C-B | Switch `run_phase_02_canonical_v1` to deterministic drain | Revert runner one line |
| C-C | Delete pass cooldown from drain output contract; migrate admin dashboards | Restore pass_fairness module |
| C-D | Remove `pass_fairness.py` imports from hot path | Git revert |

### Verification

- Golden test: fixed raw fixture → stable `receipt_hash` across two runs  
- Property: `pass_index_next` removed from execution-facing output  
- CI: extend `verify_canonical_single_drain_boundary_v1` → `verify_canonical_deterministic_selection_v1`  

---

# SECTION 2 — Execution truth unification

## 2.1 Truth surface map (today)

| Surface | Table / module | What it claims | Authoritative for execution? |
|---------|----------------|----------------|----------------------------|
| **Convergence lease** | `cortex_tenant_convergence_lease` / `execution/lease.py` | `status`, `fsm_state`, `phase_cursor`, `block_reason_code`, `pipeline_run_id` | **YES** — worker acquires lease |
| **Transition log** | `cortex_execution_transition_log` / `execution/fsm.py` | Append-only FSM transitions with `receipt_hash` | **YES** — audit of FSM |
| **Pipeline run** | `cortex_substrate_pipeline_runs` / `substrate_pipeline/repository.py` | `status`, `summary_json`, trigger | **Mirror** — created by execution, drives phase rows |
| **Phase runs** | `cortex_substrate_phase_runs` | `status`: queued/running/completed/failed/skipped/waiting | **Mirror** — UX + history |
| **Continuation** | `cortex_pipeline_continuation_states` / `pipeline_continuation.py` | waiting_on TCRE, etc. | **Legacy** — admin/recovery only; forbidden on hot path |
| **Progression receipts** | `pipeline_run.summary_json.progression_receipts` | Ad-hoc list | **Non-authoritative** |
| **Admin status** | `execution/progression_status.py` | Merges run + phase + continuation | **Read model** |

**REAL execution truth today:**

```text
CortexTenantConvergenceLease.fsm_state + phase_cursor + block_reason_code
  append-only mirrored by cortex_execution_transition_log
```

`CortexSubstratePipelineRun` is still **required** because:

- `run_tenant_convergence_v1` calls `start_substrate_pipeline_run_v1`  
- Phase runners call `begin_phase_v1` / `complete_phase_v1`  
- TCRE scope embeds `substrate_pipeline_run_id`  
- Admin routes expose pipeline history  

So: **execution owns decisions; pipeline tables are a durable audit mirror**.

## 2.2 Duplication risks

| Risk | Example |
|------|---------|
| Stale mirror | Phase `completed` with zero work while FSM still `CANONICAL_DRAINING` |
| Divergent wait | Phase row `waiting` vs lease `AWAITING_TCRE` vs continuation `waiting_on` |
| Double resume | `stalled_pipeline_recovery` + `on_tcre_job_terminal_for_execution_v1` (guarded today, fragile) |
| Operator confusion | `build_substrate_progression_status_v1` still surfaces continuation payload |

## 2.3 Target: FSM + transition log authoritative

| Surface | Target role |
|---------|-------------|
| Lease + FSM | **Authoritative** — sole “where is tenant stuck?” |
| Transition log | **Authoritative audit** — replay operator narrative |
| Pipeline run | **Optional mirror** — `mirror_only=true` metadata flag or derived view |
| Phase runs | **Derived** from phase receipts + FSM transitions |
| Continuation | **DELETE** or admin-museum only |

## 2.4 Migration plan

### Phase T1 — Read path consolidation (low risk)

- `GET execution/state` returns lease + last N transitions + **derived** phase summary (no continuation).  
- `build_substrate_progression_status_v1`: stop reading `pipeline_continuation` by default; gate behind `include_legacy_continuation=true`.  
- **Files:** `execution/progression_status.py`, `api/http/routes/admin_execution.py` (if exists).

### Phase T2 — Write path narrowing (medium risk)

- Only `apply_fsm_transition_v1` / `mark_tenant_waiting_v1` / `mark_tenant_execution_blocked_v1` mutate execution truth.  
- Phase `complete_phase_v1` must include `substrate_receipt_ref` (receipt hash pointer).  
- **Files:** `substrate_pipeline/repository.py`, `execution/fsm.py`.

### Phase T3 — Continuation tombstone (medium risk)

- Migrate `recover_stalled_pipeline_v1` to lease-only resume (already mostly true).  
- Admin 410 on continuation write APIs except explicit “museum” route.  
- Alembic: no drop yet — `FREEZE` table, stop writes.  
- **Files:** `pipeline_continuation.py`, `stalled_pipeline_recovery.py`, `orchestrator.enqueue_next_pipeline_phase_v1`.

### Phase T4 — Pipeline run demotion (high risk)

- New column `cortex_substrate_pipeline_runs.execution_mirror` default true.  
- Long-term: pipeline run ID = lease.pipeline_run_id only; no separate “running” query semantics.  
- **Blockers:** Admin UX, e2e tests, reporting.  

### Rollback

Each phase is feature-flagged; T4 requires explicit operator sign-off.

---

# SECTION 3 — Universal phase receipt contract

## 3.1 Current state (per phase)

| Phase | Output shape | receipt_hash? | Uniform outcome? |
|-------|--------------|---------------|------------------|
| 02 Canonical | `canonical_summary` nested | No | `canonical_outcome` inside summary only |
| 03 Identity | `identity_substrate_audit` rich JSON | No (has `candidate_set_sha256`) | Implicit success |
| 04 Graph | `stable_hash`, counts | Partial | Implicit |
| 05 Traversal | walk ids, counts | Partial | Implicit |
| 06 TCRE | `job_id`, `async` | No | Implicit complete |
| 07 Retrieval | index epoch fields | No | `classify_retrieval_materialization_outcome_v1` separate |
| 08 Synthesis | job counts | No | skip/fail paths |

**FSM transitions** already have `receipt_hash` in `execution/fsm.py` — but **phase bodies do not**.

## 3.2 Proposed schema: `SubstratePhaseReceiptV1`

```python
# contracts/substrate_phase_receipt.py (new)

@dataclass(frozen=True)
class SubstratePhaseReceiptV1:
    schema_version: int  # 1
    phase_id: str        # phase_02_canonical, ...
    tenant_id: str
    pipeline_run_id: str
    outcome: str         # see §4
    receipt_hash: str    # sha256:...
    processed_count: int
    blocked_reason: str | None
    input_epoch: str | None   # published index, bundle revision, etc.
    output_epoch: str | None
    started_at: str  # ISO UTC
    completed_at: str
    deterministic_version: str  # e.g. "substrate_receipt_v1"
    detail: dict[str, Any]     # phase-specific bounded payload
```

### Hash inputs (deterministic equivalence)

```text
receipt_hash = SHA256(canonical_json({
  "schema_version": 1,
  "phase_id": ...,
  "tenant_id": ...,
  "pipeline_run_id": ...,
  "outcome": ...,
  "processed_count": ...,
  "blocked_reason": ...,
  "input_epoch": ...,
  "output_epoch": ...,
  "deterministic_version": "substrate_receipt_v1",
  "detail": <phase_detail_stable_subset>,
}))
```

**Rules:**

- `detail` must exclude timestamps, Celery ids, random UUIDs unless they are **outputs of deterministic work** (e.g. `job_id` from idempotent enqueue).  
- Use existing `hash_reasoning_canonical_json_sha256_v1` from `reasoning/reasoning_receipts_proof_artifacts.py`.  

### Phase-specific `detail` subsets

| Phase | detail keys (bounded) |
|-------|----------------------|
| 02 | `bundle_id`, `canonical_outcome`, `total_succeeded`, `total_failed_rows`, `deferral_counts` |
| 03 | `bundle_id`, `candidate_set_sha256`, `counts_after` |
| 04 | `stable_hash`, `node_count`, `edge_count` |
| 05 | `primary_octs_walk_id`, `walks_materialized` |
| 06 | `tcre_job_id`, `async` |
| 07 | `published_index_epoch`, `entries_materialized`, `retrieval_outcome` |
| 08 | `jobs_enqueued`, `jobs_succeeded`, `activation_reason` |

## 3.3 Runtime integration

| Layer | Change |
|-------|--------|
| `substrate_pipeline/repository.py` | `complete_phase_v1` / `fail_phase_v1` / `wait_phase_v1` require `receipt: SubstratePhaseReceiptV1` |
| `phase_runners.py` | Wrap each `run_phase_*` with `begin` → transform → `build_receipt` → `complete` |
| `run_tenant_execution.py` | Store last phase receipt hash on lease `detail_json.last_phase_receipt_hash` |
| Admin | `GET execution/state` lists receipts inline |

### Compatibility

- `output_json` on phase runs = `receipt.detail` + `receipt_hash` + `outcome` for one release.  
- Deprecate duplicate keys after admin clients migrate.  

### Rollout order

1. Implement `build_substrate_phase_receipt_v1` helper + unit tests (no caller changes).  
2. Phase 02 + 07 (highest ambiguity).  
3. Phases 03–06, 08.  
4. CI verifier: `verify_all_phase_runners_emit_substrate_receipt_v1`.  

---

# SECTION 4 — BLOCKED semantics reconstruction

## 4.1 Current stopping semantics inventory

| Semantics | Where | Problem |
|-----------|-------|---------|
| `PHASE_STATUS_COMPLETED` | `repository.complete_phase_v1` | Can mean “success” or “no-op complete” |
| `PHASE_STATUS_WAITING` | `wait_phase_v1` (canonical topology) | Phase-local; lease may differ |
| `PHASE_STATUS_SKIPPED` | synthesis skip | Policy skip vs failure unclear |
| `LEASE_STATUS_WAITING` | `mark_tenant_waiting_v1` | TCRE async — good |
| `FSM_AWAITING_TCRE` | FSM | Good async wait |
| `FSM_BLOCKED` | `mark_tenant_execution_blocked_v1` | Only retrieval starvation path wired |
| `worker_outcome` strings | `run_tenant_execution` return | Ad-hoc: `canonical_topology_wait`, `waiting_on_tcre`, `blocked_retrieval_starvation` |
| `canonical_outcome` idle/topology_wait | drain | Not mapped 1:1 to FSM |
| `classify_retrieval_materialization_outcome_v1` | progression | `operational_starvation` vs BLOCKED |
| Fake-green risk | retrieval with 0 entries + upstream work | Partially mitigated M7 |

## 4.2 Target execution outcomes (authoritative)

**Phase receipt `outcome` (per phase):**

```text
COMPLETED          # meaningful work OR legitimate empty (idle)
COMPLETED_EMPTY    # no work possible, not blocked (e.g. no raw rows)
BLOCKED            # cannot proceed without external fact or operator
WAITING_ASYNC      # phase handoff to async job (TCRE, synthesis jobs)
FAILED             # terminal error
SKIPPED_BY_POLICY  # activation law / feature flag
```

**FSM `fsm_state` (tenant-level):**

Keep existing `FSM_*` constants in `execution/tenant_constants.py` but enforce **mutual exclusion**:

```text
AWAITING_TCRE      ⟺ WAITING_ASYNC for phase 06
BLOCKED            ⟺ lease.block_reason_code set
CANONICAL_DRAINING ⟺ phase_cursor phase_02 and outcome not terminal
IDLE               ⟺ no obligation / converged
```

### Mapping table (mandatory)

| Situation | Phase outcome | FSM | Lease status |
|-----------|---------------|-----|--------------|
| Canonical topology defer, no success | `BLOCKED` or `COMPLETED_EMPTY` + `blocked_reason=topology_wait` | `CANONICAL_DRAINING` | `RUNNING` + requeue |
| Canonical idle, backlog empty | `COMPLETED_EMPTY` | advance to `IDENTITY` | `RUNNING` |
| TCRE enqueued | `WAITING_ASYNC` | `AWAITING_TCRE` | `WAITING` |
| Retrieval starvation (retries exhausted) | `BLOCKED` | `BLOCKED` | `STALLED` |
| Synthesis forbidden backoff | `SKIPPED_BY_POLICY` | `SYNTHESIS` or `IDLE` | per policy |
| Phase 08 all jobs failed | `FAILED` | `BLOCKED` or `STALLED` | `STALLED` |

**Opinion:** Collapse `COMPLETED_EMPTY` into `COMPLETED` with `processed_count=0` **only if** `blocked_reason` is null and epoch counters unchanged — operators read `blocked_reason` first.

## 4.3 Implementation

| File | Change |
|------|--------|
| `execution/tenant_constants.py` | Add `PHASE_OUTCOME_*` constants |
| `execution/blocked.py` | Single entry `apply_execution_stop_v1(outcome, reason)` |
| `run_tenant_execution.py` | Remove stringly `worker_outcome`; use receipt outcomes |
| `phase_runners.py` | Stop calling `wait_phase_v1` without receipt; map topology_wait → receipt |
| `progression_status.py` | Derive operator classification from FSM + last receipt only |

## 4.4 Replay implications

- `BLOCKED` requires operator `admin_rerun` with `from_phase` — already supported via `execution/admin_rerun.py`.  
- `WAITING_ASYNC` requires job terminal handler only — already `on_tcre_job_terminal_for_execution_v1`.  
- Replay identity = `transition_log.receipt_hash` chain + phase receipt hashes.  

---

# SECTION 5 — Legacy runtime burial

## 5.1 Dead / legacy inventory

| Item | Path | Classification | Action |
|------|------|----------------|--------|
| Legacy post-ingest refresh | `ingestion/post_ingestion_substrate_refresh.py` | **DELETE** | No callers in repo; contains replay jobs, determinism repair, verification slice |
| Post-ingest Celery task name | `scheduling.py` lists `app.tasks.cortex_post_ingestion_substrate_refresh` | **DELETE** | Task module absent — name is phantom |
| `enqueue_next_pipeline_phase_v1` | `substrate_pipeline/orchestrator.py` | **ADMIN_ONLY** | Used by synthesis chain + stalled recovery — not execution hot path |
| `pipeline_continuation` | `substrate_pipeline/pipeline_continuation.py` | **FREEZE → DELETE** | Table remains; no hot-path writes |
| `chain_synthesis_activation_after_phase07_v1` | `operational_runtime/substrate_synthesis_activation_scheduling.py` | **MIGRATE** | Execution phase 08 owns activation; orchestrator chain admin-only |
| `drain_stub_materialize_backlog` | `canonical/transform_runtime.py` | **ADMIN_ONLY** | Ingest/legacy only after post_ingest delete |
| `run_post_ingestion_substrate_refresh` callers | — | **DELETE** | Verified zero imports |
| Progression coordinator patterns | `operational_runtime/substrate_autonomous_progression.py` | **KEEP_TEMPORARILY** | CI catalog only |
| One-off split script | `scripts/split_sync_executor_p2_step11.py` | **DELETE** | Historical |
| `schedule_substrate_pipeline_v1` vs `schedule_post_ingestion_substrate_refresh` | orchestrator + dispatch | **MIGRATE** | Unify to single `mark_dirty_and_enqueue_convergence_v1` |

## 5.2 Resurrection risk analysis

| Risk | Mitigation |
|------|------------|
| Developer calls dead post_ingest | Delete file; add CI grep ban |
| Admin doc links old path | Redirect in DOCS |
| Test imports continuation | Keep tests under `tests/.../operational_runtime/` only |

## 5.3 Deletion order

```text
L1. Delete post_ingestion_substrate_refresh.py + tests if any
L2. Unify schedule entrypoints (orchestrator → dispatch wrapper)
L3. Freeze continuation writes (runtime assert)
L4. Remove enqueue_next_pipeline_phase from synthesis hot paths
L5. Delete split script + shim comments cleanup
```

---

# SECTION 6 — TRUE P0 sign-off criteria

## 6.1 Hard invariants

```text
E1.  CortexTenantConvergenceLease.fsm_state is the sole authoritative execution cursor.
E2.  cortex_execution_transition_log is append-only and records every FSM transition.
E3.  No execution hot-path module imports operational_runtime or verify_gp085_*.
E4.  No phase runner enqueues downstream phases or Celery phase chains.
E5.  No replay job rows created on execution hot path (phases 02–08).
E6.  Every phase completion emits SubstratePhaseReceiptV1 with receipt_hash + outcome.
E7.  BLOCKED is only FSM_BLOCKED with non-null block_reason_code (no fake-green completed).
E8.  Canonical hot path uses deterministic FIFO selection (no pass cooldown / stall deprioritization).
E9.  pipeline_continuation is not written on execution hot path (table frozen or deleted).
E10. Tenant replay operator contract = execution clear + rerun only (no parallel replay FSMs).
E11. All async waits map to FSM_AWAITING_* or WAITING_ASYNC receipt outcome.
E12. post_ingestion_substrate_refresh module absent from codebase.
```

## 6.2 Verification mechanisms

| Invariant | Enforcement |
|-----------|-------------|
| E1–E2 | Integration test: slice → transitions monotonic |
| E3 | `verify_execution_hot_path_no_cesp_imports_boundary_v1` (exists) |
| E4–E5 | Extend boundary verifiers per phase |
| E6 | New `verify_substrate_phase_receipt_contract_v1` (static + sample run) |
| E7–E8 | Canonical golden + `verify_canonical_deterministic_selection_v1` |
| E9 | Existing `verify_execution_hot_path_no_continuation_boundary_v1` + continuation write ban |
| E10 | Admin API contract test |
| E11 | TCRE + synthesis terminal tests |
| E12 | CI ripgrep gate: `post_ingestion_substrate_refresh` forbidden |

**Certification pack:** Add `verify_true_p0_substrate_signoff_v1()` aggregating all checks — invoked from `verify_gp085_prog01` or separate CI job `cortex-true-p0-signoff`.

## 6.3 Operator validation

- Runbook: single page “read lease → read last transition → read last phase receipt.”  
- `build_substrate_progression_status_v1` must not contradict lease.  

---

# SECTION 7 — Implementation waves

Dependency graph:

```text
P0A (receipts) ──┬──> P0B (blocked semantics)
                 └──> P0C (canonical deterministic)
P0B + P0C ─────────────> P0D (execution truth read paths)
P0D ─────────────────────> P0E (legacy burial)
All ─────────────────────> P0F (sign-off CI + doc)
```

## P0A — Receipt standardization

| | |
|--|--|
| **Impact** | High debuggability ROI |
| **Risk** | Low–medium (schema churn in `output_json`) |
| **Files** | New `contracts/substrate_phase_receipt.py`, `phase_runners.py`, `repository.py` |
| **Migration** | Additive fields; dual-write one release |

## P0B — BLOCKED semantics

| | |
|--|--|
| **Impact** | Stops fake-green / operator confusion |
| **Risk** | Medium (FSM transition changes) |
| **Files** | `run_tenant_execution.py`, `blocked.py`, `phase_runners.py`, `progression_status.py` |
| **Depends** | P0A receipts recommended first |

## P0C — Canonical simplification completion

| | |
|--|--|
| **Impact** | Largest complexity reduction |
| **Risk** | Medium–high (materialization order changes) |
| **Files** | `drain_runtime.py`, delete gut `pass_fairness.py` hot path, `candidate_selection.py` |
| **Safety** | Shadow drain + golden fixtures before cutover |

## P0D — Execution truth unification

| | |
|--|--|
| **Impact** | Prevents regression |
| **Risk** | Medium (admin UX) |
| **Files** | `progression_status.py`, admin routes, optional DB flag on pipeline run |
| **Depends** | P0B outcomes stable |

## P0E — Legacy runtime burial

| | |
|--|--|
| **Impact** | Cognitive clarity |
| **Risk** | Low if L1 deletes truly dead code |
| **Files** | Delete `post_ingestion_substrate_refresh.py`, unify dispatch, freeze continuation |

## P0F — Deterministic sign-off + CI

| | |
|--|--|
| **Impact** | Formal certification |
| **Risk** | Low |
| **Files** | `scheduling.py`, `substrate_autonomous_progression.py`, this doc checklist |

### Estimated calendar (engineering order)

| Wave | Est. | Owner |
|------|------|-------|
| P0A | 3–5 days | execution + substrate |
| P0B | 3–4 days | execution |
| P0C | 5–8 days | canonical |
| P0D | 3–5 days | execution + admin |
| P0E | 1–2 days | ingestion + cleanup |
| P0F | 1 day | CI |

---

# SECTION 8 — Final target substrate

After TRUE P0 sign-off, Cortex substrate should present as:

## 8.1 Execution model

```text
Ingest (live) → mark dirty → convergence worker
  → for phase in [02..08]:
        receipt = deterministic_transform()
        gate(receipt)
        FSM transition(receipt.outcome)
  → async gaps (TCRE, synthesis jobs) → explicit WAITING_ASYNC → terminal resume
```

**One brain:** lease FSM. **One audit:** transition log. **One debug artifact:** phase receipt.

## 8.2 Replay model

```text
POST /admin/.../execution/clear?from_phase=X
POST /admin/.../execution/rerun
```

No parallel replay job FSMs on execution path. Canonical replay = same FIFO + deferral rules → same receipt hash.

## 8.3 Debugging model

Operator triage:

1. `lease.fsm_state` + `block_reason_code`  
2. Last 5 rows in `cortex_execution_transition_log`  
3. Last phase `receipt_hash` + `outcome` + `detail`  

## 8.4 Canonical model

```text
deterministic substrate compiler
```

Not adaptive scheduler. Topology deferrals remain the only “memory.”

## 8.5 What we deliberately do NOT build

- Pass fairness cooldowns on execution path  
- Continuation-as-orchestrator  
- Phase-local scheduling Celery chains  
- Hidden synthesis activation in phase 07  
- Multiple post-ingest refresh paths  
- Heuristic `convergence_health` driving control flow (admin hint only)  

---

## Appendix A — Code anchors (sign-off targets)

| Concern | Primary files |
|---------|---------------|
| Execution slice | `execution/run_tenant_execution.py` |
| FSM | `execution/fsm.py`, `execution/tenant_constants.py` |
| Lease | `execution/lease.py` |
| BLOCKED | `execution/blocked.py` |
| Boundaries CI | `execution/scheduling.py` |
| Phase runners | `substrate_pipeline/phase_runners.py` |
| Phase mirror | `substrate_pipeline/repository.py` |
| Canonical drain | `canonical/forward_progress/drain_runtime.py` |
| Pass fairness (delete target) | `canonical/forward_progress/pass_fairness.py` |
| Legacy post-ingest (delete target) | `ingestion/post_ingestion_substrate_refresh.py` |
| Live post-ingest | `ingestion/post_ingestion_refresh_dispatch.py` |
| Continuation (freeze) | `substrate_pipeline/pipeline_continuation.py` |

## Appendix B — Relationship to prior plans

| Document | Role |
|----------|------|
| `CORTEX_SIMPLIFICATION_AND_DETERMINISM_REFACTOR.md` | M0–M9 orchestration collapse (complete) |
| `CORTEX_PER_PHASE_SIMPLIFICATION_AUDIT.md` | Per-phase hot-path reduction P0–P3 (complete) |
| **This document** | TRUE P0 substrate sign-off (remaining work) |

When this sign-off is complete, update `CORTEX_PER_PHASE_SIMPLIFICATION_AUDIT.md` sign-off checklist to `[x]` for receipt, BLOCKED, and canonical deterministic items, and link here as the certification authority.

---

*Document owner: Cortex substrate team. Bias: execution truth over runtime cleverness.*
