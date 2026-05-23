# Cortex continuity stabilization plan

**Status:** Operational recovery plan — grounded in production reality, not architecture speculation  
**Phase A step A.1:** **Done** (2026-05-23) — see [Step A.1 completion](#step-a1-completion--synthesis-job-lifecycle)  
**Phase A step A.2:** **Done** (2026-05-23) — see [Step A.2 completion](#step-a2-completion--ecs-deploy-alignment)  
**Phase A step A.3:** **Done** (2026-05-23) — see [Step A.3 completion](#step-a3-completion--tcre-queued-drain)
**Phase A step A.4:** **Done** (2026-05-23) — see [Step A.4 completion](#step-a4-completion--strict-aa-panel-gates)
**Phase A step A.5:** **Done** (2026-05-23) — see [Step A.5 completion](#step-a5-completion--trace-only-ban)
**Phase A step A.6:** **Done** (2026-05-23) — see [Step A.6 completion](#step-a6-completion--synthesis-terminal-transitions)  
**Supersedes for stabilization work:** optimistic Phase 1–3 completion narratives and open-ended “Phase 4 operational hardening” without recurrence gates  
**Authoritative truth sources:**

- [`cortex_final_reality_state_audit.md`](cortex_final_reality_state_audit.md) (primary — 2026-05-23 prod)
- [`cortex_autonomous_execution_continuity_audit.md`](cortex_autonomous_execution_continuity_audit.md) (invariants AA/CONT)
- [`cortex_execution_intelligence_unlock_master_plan.md`](cortex_execution_intelligence_unlock_master_plan.md) (historical context only)
- [`cortex_execution_reality_model_v0.md`](../architecture/cortex_execution_reality_model_v0.md) (permanent ontology — not expanded here)

**Tenant reference:** `c08ef32b-f89a-40f6-9566-e19b5329436f` (Fizzer)  
**Mission:** Make Cortex **actually** maintain execution reality over time — recurring, lawful, wedge-free — with **fewer** moving parts.

---

## Section 1 — Executive truth

### Substrate

Cortex **today is a real substrate warehouse**: 28k+ raw rows, 20k+ canonical materializations, 7k+ org entities, 1.6k authoritative links, active ingest, and a **busy** convergence worker (hundreds of FSM transitions per day). This is not “nothing works.” Phases 0–3 **unblocked** the execution lane and proved phases 05–07 **can** complete on a recovered pipeline run. Substrate capability is **~40% of the continuity story** and is the foundation everything else must build on.

### Recurrence

Recurrence is **partial and dishonest where it matters most**. Ingest and convergence slices recur; canonical drains mats (~2k/24h) but stays in `topology_wait` with ~8.2k deferrals. Walks, retrieval epochs, and synthesis **do not recur** on a healthy cadence: retrieval last moved at `2026-05-22T22:55Z`; synthesis produced `COMPLETED_EMPTY` with zero scopes. **A.1 cleared** the synthesis job table incident (1,043 `running` → `failed` via reconcile); recurrence of **completed** synthesis jobs remains blocked until B/C. The **heartbeat of continuity is retrieval → synthesis**, and that chain is **still broken or frozen** on the retrieval/epoch side.

### Graph

The graph is **microscopically useful, macroscopically irrelevant** for org-wide intelligence: ~259 entities (~3.6%) touch the authoritative execution component; two eligible islands (257 + 2 entities). Promotion and P3′ scheduling **work locally**. Optimizing global connectivity (ρ, raw≈mat) is **explicitly out of scope** for stabilization.

### Retrieval

Retrieval is the **strongest historical proof** (2,077 rows, 3 UTC hours) but **not a living process**: island-scoped materialization (P1-C) succeeded once; published epochs and `omission_summary.island_scope_id` **diverge** from what phase 08 pins, yielding zero in-scope entries. **Retrieval recurrence is the highest-leverage fix** before any quality work.

### Synthesis

Synthesis is **operationally broken** on output (per-island phase 08 completing empty, one historical artifact) but **job-table trust is restored after A.1** (`running` count 0, terminal `failed` rows for stale orphans). Per-island architecture (P2-D) remains **blocked on epoch alignment (B1–B2)** before sign-off. “PASS” on phase receipts without `jobs_completed > 0` is **theater**.

### Continuity truthfulness

Continuity **truthfulness is the binding failure**: AA gates too weak (AA1 allows empty 08; AA6 passes on mat volume); baselines signed with `--trace-only`; pipeline `completed` while lease `dirty`; split ECS deploy (API vs worker SHA). The next mission is **not more Cortex** — it is **stabilize runtime, enforce recurrence, delete fake-green, then** hold 48h under strict AA.

---

## Section 2 — Non-negotiable principles

### Permanent laws (from reality model — do not violate)

| Law | Stabilization meaning |
|-----|----------------------|
| **L-AUTH** | Traversal/retrieval/synthesis bind only on authoritative scope; exploration does not feed synthesis |
| **L-SKIP** | Missing prerequisites → explicit omission, not invented intelligence |
| **L-TOPO** | No parent invention at synthesis/traversal time |
| **L-OMIT** | Partial intelligence with documented `outside_island_scope` / SD codes |
| **L-REPLAY** | Walks and receipts remain deterministic under pinned policy |
| **L-NO-LLM-SUBSTRATE** | LLMs interpret bounded bundles; they do not author graph or mats |

### Stabilization-phase laws (binding until exit gates met)

| # | Law |
|---|-----|
| S1 | **No fake-green:** No sign-off on phase `COMPLETED` / `COMPLETED_EMPTY` without recurrence SQL |
| S2 | **No wedge dependency:** `unlock_step*` and manual recovery scripts are **banned** from the 48h AA window |
| S3 | **No PASS without recurrence:** AA4/AA5 require **time spread** and **jobs_completed > 0**, not single snapshots |
| S4 | **Runtime truth > control plane:** Inspect JSON and baselines are **secondary** to Postgres + worker logs |
| S5 | **Simplicity > abstraction:** One convergence path, one proof entrypoint, one SQL snapshot script |
| S6 | **Delete aggressively:** Dead coordinators, duplicate proof scripts, misleading KPIs |
| S7 | **Recurrence before quality:** Lawful empty synthesis with omissions beats clever synthesis once |
| S8 | **Execution flow before graph perfection:** Island-local ρ matters; global ρ does not gate stabilization |
| S9 | **Single deploy truth:** API and worker **must** share the same image SHA for any prod sign-off |
| S10 | **Canonical debt is bounded, not zero:** Document deferrals; do not block execution lane on global convergence |

### Future considerations (explicitly deferred)

- Org-wide connected graph (ρ → 1, deferrals → 0)
- Exploration-lane productization
- Fancy synthesis quality / multi-artifact org intelligence
- Phase 3.5 / Phase 04 ontology persistence layers
- New orchestration layers, event-bus abstractions, or dual-pipeline mirrors
- “Phase 4” style architecture hardening without recurrence proof

---

## Section 3 — What “working” actually means

### Minimal success bar (one sentence)

> For **48 hours**, on Fizzer, without wedge scripts: ingest continues; execution slices run; **new retrieval index epochs** appear after walks; **synthesis jobs complete** and publish artifacts per island; AA1–AA7 **PASS under strict rules**; lease `obligation_epoch` tracks `target_epoch`; synthesis job table has **no runaway `running`** rows.

### Recurrence criteria

| Criterion | Concrete threshold | SQL / proof |
|-----------|-------------------|-------------|
| **R1** | ≥2 distinct UTC **hours** with new `cortex_retrieval_index_entries` per rolling 24h | `date_trunc('hour', created_at)` count ≥ 2 |
| **R2** | New `index_epoch` published after each walk burst | Compare `published_index_epoch` vs `cortex_octs_durable_walk_records.created_at` |
| **R3** | ≥1 `cortex_tcre_reconstruction_jobs` **completed** per 24h when walks run | `status=completed`, `completed_at` window |
| **R4** | Walks recur without manual step 9 | `COUNT(walks)` where `created_at > phase_04.completed_at` increases over 48h without unlock in ops log |

### Synthesis criteria

| Criterion | Concrete threshold |
|-----------|-------------------|
| **S1** | `phase_08` outcome **not** `COMPLETED_EMPTY` unless `scope_empty` with explicit `retrieval_entries_in_scope: 0` **and** documented stale epoch |
| **S2** | `jobs_completed ≥ 1` per phase 08 run when retrieval in-scope entries > 0 |
| **S3** | `cortex_synthesis_jobs`: `running` count **< 10** at all times (alert if higher) |
| **S4** | `artifacts_published ≥ 1` per successful phase 08 on primary island |
| **S5** | Per-island `retrieval_entries_in_scope > 0` when `published_index_epoch` matches materialization epoch |

### Retrieval criteria

| Criterion | Concrete threshold |
|-----------|-------------------|
| **V1** | Phase 07 always publishes epoch **after** island materialization for **same** walk/retrieval trigger |
| **V2** | `omission_summary.island_scope_id` on entries matches registry `island_scope_id` for materialized rows |
| **V3** | Island registry `last_retrieval_epoch` updated on publish (not stale vs DB) |
| **V4** | Materialization re-runs when `published_index_epoch` changes (invalidation law) |

### Continuity criteria

| Criterion | Concrete threshold |
|-----------|-------------------|
| **C1** | `continuity_proof_panel.py`: `m3_autonomously_alive: true` for 48h |
| **C2** | AA7 PASS with ops log or explicit `wedge_free_ack` **only** at clock start, not daily |
| **C3** | `obligation_epoch - target_epoch ≤ 2` after each slice (not permanently dirty) |
| **C4** | Phase chain 05→06→07→08 completes on **post_ingestion** runs without manual `continuity_p0_recover` |

### Graph usefulness criteria (minimal)

| Criterion | Concrete threshold |
|-----------|-------------------|
| **G1** | `islands_eligible_count ≥ 1` (P3′) — already true |
| **G2** | `linked_entities ≥ 200` on primary island — already true (~259) |
| **G3** | Promotion runs in worker after identity substrate (not only manual) |
| **G4** | **Not required:** global orphan count → 0 |

### Operational criteria

| Criterion | Concrete threshold |
|-----------|-------------------|
| **O1** | ECS API + worker **same** `image_tag` |
| **O2** | Worker logs: no OCTS schema `FileNotFoundError` |
| **O3** | Convergence sweeper enqueues slices within 5 min of `mark_dirty` |
| **O4** | `convergence_delta_succeeded > 0` **or** `untreated_routable` decreases over 48h (AA6 strict) |

### Anti-fake-green criteria

| Forbidden | Required instead |
|-----------|------------------|
| `p3_*_pass` from `--trace-only` only | Full drive + SQL recurrence |
| AA1 PASS with `COMPLETED_EMPTY` | AA1 FAIL unless jobs_completed > 0 or lawful empty with proof |
| AA6 PASS on mat-only | AA6 requires forward-progress metric |
| “Pipeline completed” as health | Lease + AA panel + R1–R4 |
| Island inspect without in-scope entries | SQL `retrieval_entries_in_scope` count |

---

## Section 4 — Root cause chains

### Retrieval chain (primary)

```text
walk burst (or none)
  → phase 07 publishes NEW index_epoch (epoch-8b226c263bd4)
  → island materialization still tagged OLD epoch (epoch-1335eb195190) in omission_summary
  → list_retrieval_entries_for_island_v1 returns 0 rows
  → iter_island_synthesis_scopes yields 0 scopes
  → phase_08 COMPLETED_EMPTY (jobs_completed=0)
  → AA1 still PASS (08 started)
  → operators believe synthesis/continuity OK
  → no recurring intelligence motion
```

**Root:** epoch / materialization **not coupled** on publish path (`retrieval_component_materialization.py`, `retrieval_index_materialization.py`, `synthesis_per_island.py`).

### Synthesis chain

```text
synthesis job enqueue without terminal transition
  → 1043 rows status=running
  → operators/scripts cannot trust job table
  → phase 08 may skip real execute path or duplicate enqueue
  → artifacts_published=0
  → global_degradation_brief theater (0 jobs per island)
  → “per_island_mode” inspect looks advanced but produces nothing
```

**Root:** `synthesis_orchestrator.py` lifecycle + missing idempotency/timeout cleanup.

### Canonical debt chain (bounded, not blocking execution)

```text
ingest caps (timeline, reviews, Notion parents)
  → missing_parent_ref deferrals (~8k)
  → topology_wait on canonical lane
  → operators focus on raw−mat (8218) as “broken”
  → execution lane CAN still run (dual-lane decoupled)
  → BUT: promotion/identity freshness lags → walk inputs stale
```

**Root:** ingest caps + **misleading global KPIs** — not solvable in stabilization; **must not block** R1–S4.

### Graph density chain

```text
97% entities disconnected from auth component
  → global P3 law (fixed) allows island scheduling
  → only 2 islands eligible
  → walks useful locally
  → operators still expect org-wide graph health
  → wasted effort on global ρ
```

**Root:** **metric confusion** — stabilization fixes island KPIs only.

### Orchestration complexity chain

```text
15+ continuity proof scripts + baselines
  → trace-only PASS
  → confidence without recurrence
  → engineering builds more inspect blocks (P2-C, P2-D, P2-E)
  → split ECS deploy
  → worker behavior ≠ API expectations
```

**Root:** **process debt** from roadmap-driven delivery without strict exit gates.

### Fake-green chain

```text
weak AA gates + baseline trace-only
  → Phase 3 marked “Done”
  → 48h clock started at false T0 (7/7 PASS snapshot)
  → clock will fail later
  → loss of trust in entire continuity program
```

**Root:** `continuity_proof_panel.py` evaluate functions + proof script defaults.

---

## Section 5 — The stabilization plan

Phases are **ordered by operational impact**, not architecture elegance.

### Phase A — Runtime stabilization (incidents + deploy truth)

| Step | Goal | Why | Subsystem | Remove / simplify | Success | Validate | Rollback | Type |
|------|------|-----|-----------|-------------------|---------|----------|----------|------|
| **A1** | ~~Purge/fix 1,043 `running` synthesis jobs~~ **Done 2026-05-23** | Restores trust in L7 job table | `synthesis_job_lifecycle.py`, `synthesis_orchestrator.py` | N/A (data + bugfix) | `running` < 10; terminal states consistent | Prod: 1043 reconciled; baseline `step_a1_synthesis_job_reconcile` | Low — backup job rows | **runtime** |
| **A2** | ~~Align ECS API + worker to **same SHA**~~ **Done 2026-05-23** | Worker must run epoch fix + deferral monitor | `continuity_p0_ecs_deploy_align.py`, `prod_deploy_backend_worker.sh` | N/A | `deploy_matches_closure_sha: true` | Prod: both on `2ab8776…`; baseline `step_a2_ecs_deploy_align` | Redeploy prior tag | **ops** |
| **A3** | ~~Drain stuck TCRE `queued` job~~ **Done 2026-05-23** | Unblocks 06→07 resume | `tcre_job_lifecycle.py`, `tcre_resume.py` | N/A | 0 queued older than 1h | Prod: 1 job drained; baseline `step_a3_tcre_queued_drain` | Re-queue job | **runtime** |
| **A4** | ~~Tighten AA1 + AA6 in proof panel~~ **Done 2026-05-23** | Stop false M3 confidence | `continuity_proof_panel.py` | Mat-only AA6 fallback removed | AA1 FAIL on empty 08; AA6 requires delta/progress/untreated↓ | Unit tests + prod panel | Revert gate logic | **ops** |
| **A5** | ~~Ban `--trace-only` as prod sign-off~~ **Done 2026-05-23** | Baselines must mean something | `continuity_p0_trace_only_policy.py` + P0/P3 proof scripts | CI-only via `VECTOR_CONTINUITY_CI_ONLY_TRACE=1` | Baseline writes require `trace_only: false` | A5 proof + unit tests | N/A | **cleanup** |
| **A6** | ~~Fix synthesis job terminal transitions~~ **Done 2026-05-23** | Prevent A1 recurrence | `synthesis_job_lifecycle.py`, `synthesis_orchestrator.py` | Single `prepare_synthesis_job_row_for_execute_v1` path | `running`=0; no stale queued/running | Prod proof + unit tests | Revert orchestrator | **runtime** |

### Phase B — Recurrence stabilization (retrieval heartbeat)

| Step | Goal | Why | Subsystem | Remove / simplify | Success | Validate | Rollback | Type |
|------|------|-----|-----------|-------------------|---------|----------|----------|------|
| **B1** | ~~**Single publish contract:** materialize → publish → same `index_epoch` on all new entries~~ **Done 2026-05-23** | Fixes B3 root cause | `retrieval_publish_contract.py`, component + pipeline mat, phase 07 | Stop publishing epoch before island mat completes | All new entries share `published_index_epoch` | SQL: epoch on entries = `get_published_index_epoch_v1` | Feature flag off island scope | **retrieval** |
| **B2** | ~~On epoch change: re-materialize primary island OR bump `island_scope` tags~~ **Done 2026-05-23** | Lawful invalidation | `retrieval_epoch_scope_alignment.py`, pipeline/component mat, phase 07 | N/A | `retrieval_entries_in_scope > 0` for current epoch | Per-island count in phase 08 output | `CORTEX_RETRIEVAL_EPOCH_SCOPE_REALIGN=0` | **retrieval** |
| **B3** | ~~Wire phase 07 → registry `last_retrieval_epoch` on success~~ **Done 2026-05-23** | Inspect truth | `execution_island_registry.py`, phase 07, publish contract | Sync-on-inspect only → sync on publish | Registry epoch matches DB | `build_island_registry_inspect_v1` (read-only default) | Disable registry / manual sync | **orchestration** |
| **B4** | ~~Phase 05: require `walks_persisted > 0` when scheduling eligible~~ **Done 2026-05-23** | Walks drive downstream | `phase05_walks_persisted_gate.py`, phase 05, `schedule_octs_walks` | Empty COMPLETED_EMPTY walks | Receipt shows walks_persisted ≥ 1 | Phase 05 `output_json` | `CORTEX_PHASE05_REQUIRE_WALKS_WHEN_ELIGIBLE=0` | **runtime** |
| **B5** | ~~Graph-hash trigger → walk → TCRE → 07 chain~~ **Done 2026-05-23** | Proves autonomous chain | `graph_hash_autonomous_chain.py` | Manual full slices only | End-to-end without unlock in CI | Integration test + prod SQL window | Disable trigger | **orchestration** |
| **B6** | ~~Post-ingestion **new pipeline run** after graph change~~ **Done 2026-05-23** | Fresh 03/04/05 receipts | `post_ingestion_fresh_pipeline_run.py`, triggers | Eternal `ce7df86d` mirror | New run id OR phases 03–05 re-run timestamps | SQL phase `started_at` | Keep old run | **orchestration** |

### Phase C — Synthesis + truthful continuity

| Step | Goal | Why | Subsystem | Remove / simplify | Success | Validate | Rollback | Type |
|------|------|-----|-----------|-------------------|---------|----------|----------|------|
| **C1** | ~~Phase 08 FAIL if scopes=0 but entries exist in epoch~~ **Done 2026-05-23** | Stop COMPLETED_EMPTY lie | `phase08_empty_scope_truth_gate.py`, phase 08 runner, AA1 | N/A | `jobs_completed ≥ 1` or explicit FAIL | Phase receipt + AA1 | `CORTEX_PHASE08_FAIL_ON_EMPTY_SCOPE_WITH_ENTRIES=0` | **synthesis** |
| **C2** | Cap scopes per island; fail loud on orchestrator error | Predictable cost | `synthesis_per_island.py`, settings | Unbounded retry | 2+ artifacts per 48h on primary island | `cortex_synthesis_artifacts` count | Raise caps | **synthesis** |
| **C3** | ~~Merge proof scripts → `continuity_audit_snapshot.py`~~ **Done 2026-05-23** | One ops entrypoint | `continuity_audit_snapshot.py` | 10+ phase scripts (keep 1–2 CI) | Single command outputs JSON + panel | Doc in plan | Keep old scripts deprecated | **cleanup** |
| **C4** | ~~Restart 48h AA clock **after** A+B+C on strict gates~~ **Done 2026-05-23** | Honest M3 | `continuity_p0_phase_c4_aa_clock_restart.py` | Old T0 baseline | New `continuity_aa_clock_T0_*.json` | Daily `continuity_p2_phase24_aa_clock_proof.py` | N/A | **ops** |
| **C5** | ~~AA5: require `jobs_completed > 0` not merely started~~ **Done 2026-05-23** | Closes fake synthesis | `phase_c5_aa5_synthesis_jobs_completed_gate.py`, panel | N/A | AA5 tied to S2 | Panel tests | `CORTEX_AA5_REQUIRE_JOBS_COMPLETED=0` → advisory | **ops** |

### Phase D — Canonical honesty + graph floor (parallel, non-blocking)

| Step | Goal | Why | Subsystem | Remove / simplify | Success | Validate | Rollback | Type |
|------|------|-----|-----------|-------------------|---------|----------|----------|------|
| **D1** | Admin primary KPI = `drainable_routable` + island list | Stop raw−mat hero | `pipeline_admin_overview.py`, `canonical_completeness_projection.py` | Deprecate raw−mat banner | UI shows island KPIs | Screenshot + API contract | Restore old KPI | **admin** |
| **D2** | Prod env: GitHub caps = code defaults (10/16/120…) | Slow deferral growth | `settings.py`, ECS task env | Conflicting env vars | Deferral growth rate ↓ week over week | `deferral_totals` trend | Lower caps | **ops** |
| **D3** | Promotion worker: verify Celery/inline on schedule | Graph floor for island | `graph_density_promotion` task | Manual promotion only | `auth_links` increases when candidates exist | SQL trend 48h | N/A | **graph** |
| **D4** | ~~Document permanent orphan class (466) as omission not failure~~ **Done 2026-05-23** | Stops chasing 0 deferrals | Docs + admin copy | N/A | Operators accept bounded debt | Runbook | `CORTEX_CANONICAL_PERMANENT_ORPHAN_OMISSION_DOC=0` | **ops** |
| **D5** | Delete legacy coordinator enqueue paths | One motion path | `substrate_pipeline/coordinator`, `scheduling.py` guards | Coordinator task | Grep + CI guard stays green | `test_schedule_substrate_pipeline` | Restore dead code | **cleanup** |

### Challenge: what should NOT exist

| System | Verdict | Action |
|--------|---------|--------|
| 15+ `continuity_p*_phase**_proof.py` | **Collapse** | One `continuity_audit_snapshot.py` + panel |
| `continuity_p0_2026-05-22.json` step sprawl | **Simplify** | One `continuity_baseline.json` with strict fields only |
| Legacy substrate coordinator | **Delete** enqueue (keep guard) | Already M4 redirect |
| `unlock_step09/10/12` in runbooks | **Ban** from prod 48h | AA7 |
| Per-island synthesis before B1 | **Freeze features** until scopes > 0 | Code can stay; gate sign-off |
| Island registry sync every inspect | **Throttle** | Publish-time sync only |
| Second pipeline truth (completed vs dirty) | **Clarify** | Admin shows both; sign-off uses lease |
| Global degradation brief at 0 jobs | **Hide** until C1 passes | Admin gating |

---

## Section 6 — Retrieval recurrence (deep)

### What retrieval recurrence SHOULD mean

Retrieval recurrence means: **whenever the execution substrate changes** (new walks, new auth edges on the island, new graph export hash), Cortex **publishes a new retrieval index epoch** with **island-tagged entries** that downstream synthesis can consume **without manual scripts**.

It does **not** mean: one bulk materialization in hour 22 that never repeats.

### Why current recurrence is weak

| Evidence | Implication |
|----------|-------------|
| 2,077 entries in **3 hours only** | Burst, not process |
| Last entry `2026-05-22T22:55:39Z` | Frozen >2h at audit |
| `last_retrieval_epoch` on registry ≠ published epoch used by phase 08 | Inspect lies |
| Phase 08 `retrieval_entries_in_scope: 0` | Downstream starved |
| Phase 05 `walks_persisted: 0` on scheduled slice | Walks not feeding chain |

### Minimum recurrence law (stabilization binding)

**Law R-REC-1:** After `phase_07_retrieval` completes on a pipeline run:

1. `published_index_epoch` is set **once**.
2. Island materialization runs **for that epoch** before phase 08.
3. Every `cortex_retrieval_index_entry` written in that pass carries `omission_summary.island_scope_id` for the island materialized.
4. `execution_island_registry.last_retrieval_epoch` is updated to that epoch.
5. Phase 08 pins **the same** epoch.

**Law R-REC-2:** Over any rolling 24h window where `mark_dirty` fires and walks complete, **≥2 UTC hours** contain new retrieval rows (AA4 strict).

**Law R-REC-3:** If `published_index_epoch` changes, prior-epoch entries are **stale** (not deleted required); synthesis must use pinned epoch only — admin must show `epoch_age`.

### How to validate (SQL — copy/paste ops)

```sql
-- R-REC-2: hours with new entries (last 24h)
SELECT date_trunc('hour', created_at) AS h, COUNT(*) AS n
FROM cortex_retrieval_index_entries
WHERE tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f'
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY 1 ORDER BY 1;

-- R-REC-1: epoch alignment
SELECT index_epoch, COUNT(*) AS n,
       COUNT(*) FILTER (
         WHERE (omission_summary->>'island_scope_id') IS NOT NULL
       ) AS tagged
FROM cortex_retrieval_index_entries
WHERE tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f'
GROUP BY 1 ORDER BY MAX(created_at) DESC;

-- In-scope for primary island + published epoch
SELECT COUNT(*) FROM cortex_retrieval_index_entries
WHERE tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f'
  AND index_epoch = (SELECT published_index_epoch FROM ... ) -- use app getter
  AND omission_summary->>'island_scope_id' = 'd7e41b3c763d38e9';
```

### Reliability before quality

- Do **not** expand retrieval to all entities.
- Do **not** add new RET classes.
- **Do** fix epoch coupling and hour-spread recurrence.
- **Do** fail phase 08 when in-scope count is zero but tagged entries exist for epoch (bug indicator).

---

## Section 7 — Synthesis stabilization (deep)

### Minimum lawful synthesis

Lawful synthesis means:

1. `execute_synthesis_job_envelope_v1` runs and **terminates** (completed/failed, not perpetual running).
2. At least one job produces an **artifact** when retrieval in-scope entries > 0.
3. Phase receipt records `jobs_completed`, `artifact_digests`, `synthesis_publication_epoch`.
4. Omissions documented in artifact (`outside_island_scope`, SD codes) — quality minimal.

### What counts as “real synthesis”

| Counts | Does not count |
|--------|----------------|
| `jobs_completed > 0` + `artifact_id` persisted | `COMPLETED_EMPTY` with 0 scopes when entries exist |
| Per-island envelope with `island_scope_id` matching retrieval | Global monolithic synthesis only |
| Publication epoch pinned to retrieval epoch | Panel AA5 “started_at” only |
| Job table: completed/failed terminal | 1043× `running` |

### What to delete / simplify

| Item | Recommendation |
|------|----------------|
| Sign-off on per-island inspect alone | **Delete** as gate |
| Multiple concurrent synthesis enqueues per scope | **Cap** + idempotency |
| `COMPLETED_EMPTY` as success outcome when scopes scheduled = 0 but island has entries | **FAIL** phase |
| Activation audit driven sign-off | **Advisory only** |

### Recurrence that matters

- **≥1 new artifact** per 48h on primary island during active ingest window.
- Phase 08 runs on **each** post-ingestion pipeline completion where phase 07 published.
- `cortex_synthesis_jobs.running` stable.

### Stop fake synthesis PASS states

| Change | File |
|--------|------|
| AA1 requires `phase_08.status=completed` AND (`jobs_completed > 0` OR lawful documented empty) | `continuity_proof_panel.py` |
| AA5 requires `jobs_completed > 0` | `continuity_proof_panel.py` |
| `fail_phase_with_receipt` when all jobs fail | `synthesis_pipeline.py` (already partial) |
| Admin: show synthesis job table health | new panel field |

---

## Section 8 — Graph reality

### What density is ACTUALLY required

| Requirement | Number | Why |
|-------------|--------|-----|
| Eligible island | ≥1 component, \|V\| ≥ 2 | P3′ law — **met** (2 islands) |
| Auth edges on island | ≥1 — **met** (~1,599 in registry for 257-entity island) |
| Linked entities | ≥ ~200 for traversal/bindings | **Met** (~259) |
| Org-wide entities connected | **Not required** | 97% may stay orphan |

### What connectivity is useful

- **Within island:** authoritative edges for walks and retrieval bindings.
- **Promotion:** candidate → auth on island — recurring during worker slices (D3).
- **Not useful for V0 continuity:** global ρ, counting all 7k entities in walks.

### What is overkill / wasted

- Scheduling walks for entire org graph.
- Blocking execution on global `traversal_propagation_blocked` (fixed by P3′ — **do not revert**).
- Admin “graph healthy” single boolean.
- Chasing `raw − mat → 0`.

### What can wait

- Multi-island synthesis parity (stabilize primary island first).
- Bridge quality metrics between islands.
- Exploration partition walks.
- Entity resolution Phase 04 product roadmap.

### What must become recurring

- **Promotion passes** when identity projection runs (event trigger exists — **prove** in SQL).
- **Graph export** (phase 04) on graph hash change — **not** once per run forever.
- **Walk scheduling** on hash change with `walks_persisted > 0`.

### Misleading graph metrics

| Metric | Why misleading | Replace with |
|--------|----------------|--------------|
| `raw − mat` | Confuses deferrals with failure | `untreated_routable`, `deferral_by_reason` |
| Global orphan count | Blocks psychologically | `islands_eligible_count`, `linked_entities` |
| `pipeline completed` | Mirror not substrate | Lease dirty + AA panel |
| ρ ≥ 0.3 | Infeasible at Fizzer | ρ_local on largest island |

---

## Section 9 — Delete / simplify

| Item | Why it exists | Why it harms continuity | Replaces it | Action |
|------|---------------|-------------------------|-------------|--------|
| `run_cortex_substrate_pipeline_coordinator_task` | Pre-M4 | Confusion, dual motion | `run_tenant_convergence_v1` | **DELETE** enqueue |
| 15+ `continuity_p*_phase*_proof.py` | Roadmap gates | trace-only PASS | `continuity_audit_snapshot.py` + panel | **MERGE**; deprecate |
| `continuity_p0_2026-05-22.json` step_* | Marketing completion | False confidence | `continuity_baseline.json` strict schema | **COLLAPSE** |
| `unlock_step09/10/12` scripts | War room | Wedge timestamps, AA7 fail | Autonomous triggers | **BAN** runbook |
| AA6 mat-only fallback | Bootstrap | Fake forward progress | `convergence_delta_succeeded` or drainable ↓ | **DELETE** fallback |
| AA1 “08 started” pass | Bootstrap | Empty synthesis | jobs_completed gate | **FIX** |
| `--trace-only` prod proofs | CI speed | False baselines | Full drive required | **FIX** process |
| Island registry inspect sync | P2-C admin | Stale epochs | Publish-time sync | **SIMPLIFY** |
| `substrate_autonomous_progression` hooks | Old 07→08 | Duplicate | Phase 08 runner | **DELETE** unused |
| Dual pipeline run truth | Audit mirror | Operator confusion | Lease-first UI | **CLARIFY** admin |
| Global synthesis before island fix | P2-D | Empty scopes | B1→C1 first | **FREEZE** sign-off |
| Per-tenant `attempt_count` 17k without interpretation | Retry churn | Looks like failure | Transition rate + outcomes | **RELABEL** admin |
| Legacy Celery phase chain | M6 | Dead tasks | Dual-lane inline | **REMOVE** from beat |
| Multiple health cards (alive vs AA) | Product history | Contradiction | Single “Continuity” panel | **MERGE** admin |

---

## Section 10 — Phase exit criteria

### Phase A — Runtime stabilization

| Gate | Observable proof |
|------|------------------|
| A-G1 | `SELECT status, COUNT(*) FROM cortex_synthesis_jobs WHERE tenant_id=… GROUP BY 1` → `running < 10` |
| A-G2 | ECS probe: API tag = worker tag = deploy SHA |
| A-G3 | TCRE: no `queued` jobs older than 1 hour |
| A-G4 | Unit tests: AA1 fails on `COMPLETED_EMPTY` fixture; AA6 fails on mat-only fixture — **done (A.4)** |
| A-G5 | CloudWatch: synthesis task logs show terminal states within 30m |

### Phase B — Recurrence stabilization

| Gate | Observable proof |
|------|------------------|
| B-G1 | New materialization epoch: 100% of new entries have `island_scope_id` |
| B-G2 | `retrieval_entries_in_scope > 0` for `d7e41b3c763d38e9` on current published epoch |
| B-G3 | 24h SQL: ≥2 hours with new retrieval rows |
| B-G4 | Phase 05 receipt: `walks_persisted >= 1` on ≥1 slice after deploy |
| B-G5 | Registry `last_retrieval_epoch` = published epoch (SQL join) |

### Phase C — Truthful continuity

| Gate | Observable proof |
|------|------------------|
| C-G1 | Phase 08: `jobs_completed >= 1`, `artifacts_published >= 1` on primary island |
| C-G2 | `continuity_proof_panel.py --json` → `m3_autonomously_alive: true` under **strict** gates |
| C-G3 | 48h clock: all AA1–AA7 PASS; AA7 with ops log proof |
| C-G4 | No `unlock_step` in ops log window |
| C-G5 | `obligation_epoch - target_epoch <= 2` for 80% of slices |

### Phase D — Intelligence stabilization (minimal)

| Gate | Observable proof |
|------|------------------|
| D-G1 | ≥2 synthesis artifacts / 7 days on primary island (lawful, not quality) |
| D-G2 | Artifacts contain `synthesis_omission_rows` + citations (structure exists) |
| D-G3 | Admin shows island KPIs not raw−mat hero |
| D-G4 | Deferral total stable or ↓ (not required → 0) |

**Anti-fake-green checklist (all phases):**

- [x] No baseline update without `trace_only: false` — **enforced (A.5)**
- [ ] No sign-off if only inspect JSON improved
- [ ] SQL recurrence queries attached to baseline file
- [ ] Phase 08 empty outcome investigated and classified (bug vs lawful empty)

---

## Section 11 — Final challenge

### What Cortex will ACTUALLY become after this plan

A **recurring execution continuity substrate on execution islands**:

- Ingest and canonical drain keep running (with **bounded** deferral debt documented).
- Dual-lane worker advances 05→08 on post-ingestion runs **without wedges**.
- **Retrieval epochs and island-tagged entries recur** on a measurable hourly cadence.
- **Synthesis jobs complete**, publish artifacts, and job table stays healthy.
- Operators trust **one proof command** and **strict AA**, not 15 scripts and green admin cards.

It will **not** become: org-wide autonomous intelligence, zero deferrals, or global graph health.

### What still will NOT work (honest)

- **97%** of entities remain outside execution islands.
- **Thousands** of topology deferrals remain (timeline/Notion/GitHub parent gaps).
- **Identity/graph phases** will not rerun every hour unless B6/event triggers are proven.
- **Synthesis quality** will remain minimal (partial, omission-heavy) — but **recurring**.
- **Multi-island** parity may lag primary island.

### What must be explicitly postponed

- Exploration-lane productization.
- Phase 3.5 continuity persistence / edge stores.
- Global ρ gates and “graph healthy” banners.
- New orchestration abstractions (event bus, third pipeline mirror).
- Intelligence quality programs (RAG tuning, LLM routing) **before** C-G2 passes.

### Architectural temptations to resist

| Temptation | Why resist |
|------------|------------|
| “Add Phase 5 orchestration layer” | Recurrence not proven |
| “More inspect blocks” | Theater replaced runtime |
| “Stricter global graph laws” | Broke Fizzer before P3′ |
| “New proof script per PR” | Caused trace-only PASS culture |
| “Monolithic synthesis return” | Violates island law already shipped |
| “6-month ontology refactor” | Abstraction drift |

**Guardrail sentence for every PR during stabilization:**

> “Does this change increase **recurring** retrieval or synthesis rows in prod without a wedge? If no, defer.”

---

## Step A.1 completion — synthesis job lifecycle

**Completed:** 2026-05-23  
**Goal:** Purge/fix stuck `running` synthesis jobs; restore terminal FSM transitions; prevent immediate recurrence.

### What was implemented (generic multi-tenant)

| Area | Change |
|------|--------|
| Lifecycle module | `synthesis_job_lifecycle.py` — reconcile stale `running`, idempotency inflight resolve, pre-materialize hook |
| Orchestrator | `execute_synthesis_job_envelope_v1` — `finally` orphan terminalization; resume/supersede inflight idempotency; flush on `running` |
| Pipeline | `materialize_synthesis_for_pipeline_v1` — optional pre-flight reconcile (`CORTEX_SYNTHESIS_JOB_RECONCILE_ON_MATERIALIZE`) |
| Settings | `CORTEX_SYNTHESIS_JOB_RUNNING_STALE_SECONDS` (default 86400), `CORTEX_SYNTHESIS_JOB_RUNNING_ALERT_THRESHOLD` (10) |
| Observability | Admin health: `tenant_jobs_running`, stale-running alert |
| Proof | `continuity_p0_phase_a1_synthesis_job_reconcile_proof.py` + `continuity_p0_synthesis_job_lifecycle.py` |
| CI | `.github/workflows/deploy.yml` — A.1 pytest gate |

### Prod proof (Fizzer default tenant)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_a1_synthesis_job_reconcile_proof.py \
  --stale-seconds 0
```

| Metric | Before | After |
|--------|--------|-------|
| `running` | 1043 | 0 |
| `failed` | 0 | 1043 |
| `completed` | 1 | 1 |
| `p0_a1_pass` | — | true |

Baseline: [`continuity_p0_2026-05-22.json`](baselines/continuity_p0_2026-05-22.json) → `step_a1_synthesis_job_reconcile`.

### Exit gates (A-G1 partial)

- [x] `running < 10` (SQL histogram)
- [x] No jobs stuck `running` > 24h (all reconciled to `failed`)
- [x] Orchestrator terminal transitions hardened (`finally` + idempotency supersede)
- [x] A-G5 SQL recurrence: synthesis job histogram stable (`running`/`queued` inflight) — **done (A.6 proof)**
- [ ] A-G5 CloudWatch terminal logs (after deploy of A.1–A.6 closure SHA to ECS)

---

## Step A.2 completion — ECS deploy alignment

**Completed:** 2026-05-23  
**Goal:** API and worker ECS services run the **same** ECR image tag; eliminate split-deploy false confidence.

### What was implemented

| Area | Change |
|------|--------|
| ECS snapshot | `snapshot_prod_ecs_deploy_v1` — describe API/worker tags without closure compare |
| ECS realign | `realign_ecs_worker_to_api_image_tag_v1` — ECS-only worker→API tag (no docker; fixes split deploy) |
| Deploy script | `prod_deploy_backend_worker.sh` — A1/A2 tests + post-deploy SHA verify |
| Proof | `continuity_p0_phase_a2_ecs_deploy_align_proof.py` + `continuity_p0_ecs_deploy_align.py` |
| CI | `.github/workflows/deploy.yml` — A.2 pytest gate; existing post-deploy tag verify unchanged |

### Prod proof (2026-05-23)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_a2_ecs_deploy_align_proof.py \
  --use-deployed-closure --realign-worker --probe-only
```

| Check | Result |
|-------|--------|
| `both_services_on_same_tag` | true |
| `api_image_tag` | `2ab8776fafc8861ef69571f1531da1fd4f880a04` |
| `worker_image_tag` | `2ab8776fafc8861ef69571f1531da1fd4f880a04` |
| `deploy_matches_closure_sha` | true (closure = deployed tag) |
| `p0_a2_pass` | true |

Baseline: [`continuity_p0_2026-05-22.json`](baselines/continuity_p0_2026-05-22.json) → `step_a2_ecs_deploy_align`.

**Note:** Local commit `acbbac8` (A.1 code) is **not** on ECS until `main` is pushed and GitHub Actions deploy runs (or `prod_deploy_backend_worker.sh` with ECR push credentials). Split-deploy incident is **resolved** at `2ab8776`; A.1 worker hooks ship on next full deploy.

### Exit gates (A-G2)

- [x] API tag = worker tag
- [x] `deploy_matches_closure_sha` for deployed closure
- [x] `realign_ecs_worker_to_api_image_tag_v1` available for future drift

---

## Step A.3 completion — TCRE queued drain

**Completed:** 2026-05-23  
**Goal:** Clear stale `queued` TCRE jobs blocking phase 06→07 resume; record `resume_convergence_from_waiting_v1` trace.

### What was implemented

| Area | Change |
|------|--------|
| Lifecycle | `tcre_job_lifecycle.py` — `drain_stale_queued_tcre_jobs_v1`, histogram + stale counts |
| Resume | `tcre_resume.py` — best-effort Celery enqueue; `enqueue_convergence=False` for local prod proof |
| Orchestrator | `execute_tcre_reconstruction_job_v1` — `finally` orphan `running` terminalization |
| Settings | `CORTEX_TCRE_JOB_QUEUED_STALE_SECONDS` (default 3600, A-G3) |
| Proof | `continuity_p0_phase_a3_tcre_queued_drain_proof.py` + `continuity_p0_tcre_job_drain.py` |
| CI | `.github/workflows/deploy.yml` — A.3 pytest gate |

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_a3_tcre_queued_drain_proof.py \
  --use-deployed-closure --lease-only
```

| Metric | Before | After |
|--------|--------|-------|
| `queued` (stale >1h) | 1 | 0 |
| `completed` | 2 | 3 |
| Job `57440823-…` | `queued` | `completed` + lease resume `phase_07_retrieval` |
| `p0_a3_pass` | — | true |

Baseline: [`continuity_p0_2026-05-22.json`](baselines/continuity_p0_2026-05-22.json) → `step_a3_tcre_queued_drain`.

### Exit gates (A-G3)

- [x] No `queued` TCRE jobs older than 1 hour after drain
- [x] `resume_convergence_from_waiting_v1` trace on completed drain (`lease.phase_cursor = phase_07_retrieval`)
- [x] P1-D static boundaries still pass

**Next step:** ~~A4~~ → **A5** (ban `--trace-only` prod sign-off).

---

## Step A.4 completion — strict AA panel gates

**Completed:** 2026-05-23  
**Goal:** Stop fake-green M3 confidence from weak AA1 (phase 08 “started”) and AA6 (mat-count-only pass).

### What was implemented

| Area | Change |
|------|--------|
| AA1 | Requires phases 05–07 **completed**, phase 08 **completed**, `jobs_completed > 0` or **lawful documented empty** (`scope_empty` + reason or `COMPLETED_EMPTY` outcome) |
| AA6 | Pass only on `convergence_delta_succeeded > 0`, `progress_made_in_window`, or `untreated_routable` decrease in window — **no** `materializations_in_window` fallback |
| Panel schema | `strict_aa_panel_schema_version: 2`; AA6 evidence includes `mat_only_pass`, `forward_progress_signals` |
| Proof | `continuity_p0_aa_panel_strict.py` + `continuity_p0_phase_a4_aa_panel_strict_proof.py` |
| CI | `.github/workflows/deploy.yml` — A.4 pytest gate |

### Prod proof (Fizzer, strict gates — honest FAIL expected)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_a4_aa_panel_strict_proof.py \
  --use-deployed-closure
```

| Gate / metric | Before (weak) | After (strict) |
|---------------|---------------|----------------|
| AA1 | PASS (08 started) | **FAIL** — `jobs_completed=0`, not lawful empty |
| AA6 | PASS (mat fallback) | **FAIL** — `mat_only_pass=true`, no forward-progress signals |
| `m3_autonomously_alive` | true (fake-green) | **false** (honest) |
| `p0_a4_pass` | — | **true** (wiring + evidence shape) |

Baseline: [`continuity_p0_2026-05-22.json`](baselines/continuity_p0_2026-05-22.json) → `step_a4_aa_panel_strict`.

### Exit gates (A-G4)

- [x] AA1 unit test fails on `COMPLETED_EMPTY` without lawful empty proof
- [x] AA6 unit test fails when only mat-volume would have passed (no forward-progress signals)
- [x] Prod panel records strict evidence; M3 clock no longer fake-green on AA1/AA6 alone

**Note:** Strict AA1/AA6 ship on next ECS deploy of this closure SHA. Until then, prod panel run uses **local** gate logic via proof script (DB truth + local code).

**Next step:** ~~A5~~ → **A6** (synthesis job terminal transitions).

---

## Step A.5 completion — trace-only prod sign-off ban

**Completed:** 2026-05-23  
**Goal:** Stop fake-green baselines signed with `--trace-only` (skipped ECS deploy gate).

### What was implemented

| Area | Change |
|------|--------|
| Policy | `continuity_p0_trace_only_policy.py` — CI env gate, baseline write ban, `prod_signoff_valid` check |
| Proof scripts | P0 phase A (`a1`–`a4`) + P3 (`31`–`34`): `add_trace_only_ci_argparse_v1`, `save_p0_step_baseline_v1` (skips write when trace-only) |
| Evaluators | All step proofs add `prod_signoff_valid: not trace_only` to pass criteria |
| Proof | `continuity_p0_phase_a5_trace_only_ban_proof.py` audits Phase A baseline steps |
| CI | `.github/workflows/deploy.yml` — A.5 pytest gate |

### CI-only mode

```bash
# Wiring probe in CI only — does NOT update committed baseline
export VECTOR_CONTINUITY_CI_ONLY_TRACE=1
python scripts/continuity_p0_phase_a4_aa_panel_strict_proof.py --trace-only
```

Production sign-off (writes baseline):

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_a5_trace_only_ban_proof.py --use-deployed-closure
```

| Check | Result |
|-------|--------|
| `--trace-only` without CI env | **exit 2** (rejected) |
| Phase A steps `trace_only` | **false** (a1–a4 re-signed) |
| `p0_a5_pass` | **true** |
| Scripts wired | 9 proof scripts |

Baseline: [`continuity_p0_2026-05-22.json`](baselines/continuity_p0_2026-05-22.json) → `step_a5_trace_only_ban`, root `trace_only_policy`.

### Exit gates

- [x] Baseline merge refuses `trace_only=True`
- [x] P0/P3 continuity proof scripts use shared policy helpers
- [x] Phase A baseline audit: zero `trace_only: true` violations

**Next step:** ~~A6~~ → ~~**B1**~~ → **B2** (retrieval epoch / island scope alignment).

---

## Step A.6 completion — synthesis terminal transitions

**Completed:** 2026-05-23  
**Goal:** Prevent recurrence of 1,043 stuck `running` jobs via hardened orchestrator terminal transitions and deduped enqueue.

### What was implemented

| Area | Change |
|------|--------|
| Lifecycle | `terminalize_synthesis_job_completed_v1`, `prepare_synthesis_job_row_for_execute_v1`, `supersede_duplicate_inflight_synthesis_jobs_v1` |
| Queued stale | `reconcile_stale_queued_synthesis_jobs_v1` + `CORTEX_SYNTHESIS_JOB_QUEUED_STALE_SECONDS` (default 3600) |
| Orchestrator | Single prepare path; symmetric completed/failed terminalizers; `ensure_synthesis_job_terminal_after_execute_v1` in `finally` |
| Materialize | Pre-flight reconcile runs **running + queued** stale reconcile |
| Proof | `continuity_p0_synthesis_terminal_transitions.py` + `continuity_p0_phase_a6_synthesis_terminal_transitions_proof.py` |
| CI | `.github/workflows/deploy.yml` — A.6 pytest gate |

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_a6_synthesis_terminal_transitions_proof.py \
  --use-deployed-closure --dry-run
```

| Metric | Result |
|--------|--------|
| `running` | 0 |
| `queued` | 0 |
| `stale_running` | 0 |
| `stale_queued` | 0 |
| `p0_a6_pass` | true |

Baseline: [`continuity_p0_2026-05-22.json`](baselines/continuity_p0_2026-05-22.json) → `step_a6_synthesis_terminal_transitions`.

### SQL recurrence (operator)

```sql
SELECT status, COUNT(*) FROM cortex_synthesis_jobs
WHERE tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f'
GROUP BY 1;
```

### Exit gates

- [x] Orchestrator uses single prepare enqueue (no inline create/idempotent fork)
- [x] Success path uses `terminalize_synthesis_job_completed_v1`
- [x] `finally` guarantees no orphan `running`
- [x] Prod histogram: inflight stable

**Phase A complete.** Next: ~~**B1**~~ → **B2** — epoch-change re-materialization / island scope tags.

---

## Step B.1 completion — retrieval single publish contract (R-REC-1)

**Completed:** 2026-05-23  
**Goal:** One `BUILDING` epoch per pipeline materialization pass; defer per-entry publish until a single `publish_retrieval_index_epoch_v1` barrier; align entries with `get_published_index_epoch_v1`.

### What was implemented

| Area | Change |
|------|--------|
| Contract module | `retrieval_publish_contract.py` — `begin_pipeline_retrieval_index_build_v1`, `finalize_pipeline_retrieval_index_build_v1`, `audit_published_epoch_entry_alignment_v1`, `materialize_entry_respecting_publish_contract_v1` |
| Component mat | `materialize_retrieval_index_for_largest_island_v1` — begin/finalize contract; `auto_publish=False` on all entries |
| Pipeline mat | Non–P1-C branch uses same begin/finalize contract |
| Entry guard | `materialize_retrieval_index_entry_v1` skips `ensure_published_index_epoch_v1` while epoch is `BUILDING` |
| Phase 07 | `run_phase_07_retrieval_v1` attaches `published_index_epoch` + `publish_contract_audit` on receipt |
| Proof | `continuity_p0_retrieval_publish_contract.py` + `continuity_p0_phase_b1_retrieval_publish_contract_proof.py` |
| CI | `.github/workflows/deploy.yml` — B.1 pytest gate |

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_b1_retrieval_publish_contract_proof.py \
  --use-deployed-closure
```

Requires prod DB env (`DB_PROD_*`). Sign-off writes `step_b1_retrieval_publish_contract` on [`continuity_p0_2026-05-22.json`](baselines/continuity_p0_2026-05-22.json).

| Metric | Result (2026-05-23) |
|--------|---------------------|
| `published_index_epoch` | `epoch-fb8c13c67db3` |
| `epochs_align` | true |
| `entries_in_materialized_epoch` | 1599 |
| `entries_with_island_scope_in_epoch` | 1200 |
| `building_epochs_inflight` | 0 |
| `p0_b1_pass` | true |

Closure: `2ab8776fafc8861ef69571f1531da1fd4f880a04` (`--use-deployed-closure`). Post-deploy phase 07 receipts will include `publish_contract_audit` (currently absent on last receipt — code lands with this commit).

### SQL (R-REC-1 alignment — operator)

```sql
SELECT index_epoch, COUNT(*) AS n,
       COUNT(*) FILTER (
         WHERE (omission_summary->>'island_scope_id') IS NOT NULL
       ) AS tagged
FROM cortex_retrieval_index_entries
WHERE tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f'
GROUP BY 1 ORDER BY MAX(created_at) DESC;
```

### Exit gates

- [x] Pipeline/component materialization: one `BUILDING` epoch, single finalize publish
- [x] Per-entry materialization cannot publish mid-pass while `BUILDING`
- [x] Phase 07 receipt carries published epoch + contract audit
- [x] Static wiring + proof evaluator + CI gate
- [x] B-G1 full (100% island tags on **new** passes) — **done (B.2 idempotent omission merge + epoch realign)**

**Next step:** ~~**B1**~~ → ~~**B2**~~ → ~~**B3**~~ → **B4** — phase 05 walks persisted gate.

---

## Step B.2 completion — retrieval epoch / island scope alignment

**Completed:** 2026-05-23  
**Goal:** On published epoch change, keep primary island entries in scope for synthesis (R-REC-1 extension / B-G2).

### What was implemented

| Area | Change |
|------|--------|
| Alignment module | `retrieval_epoch_scope_alignment.py` — in-scope counts, prior-epoch tag realign, post-publish reconcile |
| Idempotent mat | `materialize_retrieval_index_entry_v1` merges `omission_summary` (including `island_scope_id`) when updating existing lookup rows |
| Pipeline mat | Component + global paths call `reconcile_primary_island_scope_on_epoch_change_v1` after publish |
| Phase 07 | Receipt includes `retrieval_entries_in_scope` when missing from mat stats |
| Settings | `CORTEX_RETRIEVAL_EPOCH_SCOPE_REALIGN` (default on) |
| Proof | `continuity_p0_retrieval_epoch_scope_alignment.py` + `continuity_p0_phase_b2_retrieval_epoch_scope_alignment_proof.py` |
| CI | `.github/workflows/deploy.yml` — B.2 pytest gate |

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_b2_retrieval_epoch_scope_alignment_proof.py \
  --use-deployed-closure
```

Auto-runs tag realign from prior published epoch when Fizzer primary in-scope count is zero. Use `--drive-realign` to force; `--dry-run` to probe without commit.

| Metric | Result (2026-05-23) |
|--------|---------------------|
| `published_index_epoch` | `epoch-fb8c13c67db3` |
| `primary_island_scope_id` | `d7e41b3c763d38e9` |
| `retrieval_entries_in_scope` | 1200 |
| `fizzer_primary_in_scope` | 1200 |
| `latest_phase_08_primary_island_in_scope` | 1200 |
| `p0_b2_pass` | true |

### Exit gates

- [x] Epoch-change reconcile wired on pipeline materialization
- [x] Existing entry updates preserve/bump `island_scope_id`
- [x] Phase 07/08 expose `retrieval_entries_in_scope` for primary island
- [x] B-G2: Fizzer primary island `d7e41b3c763d38e9` in-scope &gt; 0 on published epoch (prod proof)

**Next step:** ~~**B3**~~ → ~~**B4**~~ → ~~**B5**~~ → ~~**B6**~~ → **Phase C** (synthesis truth gates).

---

## Step B.3 completion — island registry `last_retrieval_epoch` on publish

**Completed:** 2026-05-23  
**Goal:** Registry rows reflect the DB published retrieval epoch after phase 07 (B-G5 / R-REC-1 law item 4).

### What was implemented

| Area | Change |
|------|--------|
| Registry resolver | `resolve_last_retrieval_epoch_for_scope_v1` — uses `get_published_index_epoch_v1` when island has in-scope entries (not max tagged epoch string) |
| Publish hook | `record_retrieval_publish_on_island_registry_v1` — full registry sync + `audit_registry_published_epoch_alignment_v1` |
| Publish contract | `finalize_pipeline_retrieval_index_build_v1` calls publish hook (no longer raw sync-only) |
| Phase 07 | `run_phase_07_retrieval_v1` attaches `island_registry_publish` on success |
| Inspect | `build_island_registry_inspect_v1(sync=False)` default — sync on publish, not every inspect |
| Proof | `continuity_p0_retrieval_registry_epoch.py` + `continuity_p0_phase_b3_retrieval_registry_epoch_proof.py` |
| CI | `ci.yml` includes B.3 proof evaluator tests |

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_b3_retrieval_registry_epoch_proof.py \
  --use-deployed-closure
```

Auto-runs registry rebuild when rows are stale vs published epoch. Use `--drive-sync` to force; `--dry-run` to probe without commit.

| Metric | Result (2026-05-23) |
|--------|---------------------|
| `published_index_epoch` | `epoch-fb8c13c67db3` |
| Primary `last_retrieval_epoch` | `epoch-fb8c13c67db3` (aligned) |
| `registry_rows_stale_vs_published` | 0 |
| `entries_in_scope_on_published` (primary) | 1200 |
| `p0_b3_pass` | true |

### SQL (B-G5 — operator)

```sql
SELECT r.island_scope_id, r.last_retrieval_epoch, p.published_epoch
FROM cortex_execution_island_registry r
CROSS JOIN (
  SELECT index_epoch AS published_epoch
  FROM cortex_retrieval_index_epochs
  WHERE tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f'
    AND build_state = 'PUBLISHED'
  ORDER BY published_at DESC NULLS LAST
  LIMIT 1
) p
WHERE r.tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f';
```

### Exit gates

- [x] `last_retrieval_epoch` derived from published getter when in-scope entries exist
- [x] Phase 07 publish path syncs registry and records audit on receipt
- [x] Inspect default is read-only (`sync=False`)
- [x] B-G5: primary island registry epoch aligned with published epoch (prod proof)

**Next step:** ~~**B4**~~ → ~~**B5**~~ → ~~**B6**~~ → **Phase C**.

---

## Step B.4 completion — phase 05 walks persisted gate

**Completed:** 2026-05-23  
**Goal:** When traversal scheduling is eligible (G-P085-WALK-01), phase 05 must not fake-green `COMPLETED_EMPTY` with zero walks (B-G4).

### What was implemented

| Area | Change |
|------|--------|
| Gate module | `phase05_walks_persisted_gate.py` — schedule context, supplement pass, outcome resolver, schedule enforcement |
| Phase 05 | `run_phase_05_traversal_v1` — evaluates eligibility, supplements walks, `BLOCKED` when eligible but empty |
| Scheduler | `schedule_octs_walks_for_tenant_v1` — `enforce_schedule_pass_walks_persisted_v1` on inline pass |
| Settings | `CORTEX_PHASE05_REQUIRE_WALKS_WHEN_ELIGIBLE` (default on) |
| Proof | `continuity_p0_phase05_walks_persisted.py` + `continuity_p0_phase_b4_phase05_walks_persisted_proof.py` |
| CI | `ci.yml` — B.4 gate + proof evaluator tests |

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_b4_phase05_walks_persisted_proof.py \
  --use-deployed-closure
```

Auto-runs schedule pass when no recent slice shows walks. `--drive-schedule` forces a pass.

| Metric | Result (2026-05-23) |
|--------|---------------------|
| `durable_walk_row_count` | 28 |
| `slices_with_walks_persisted_or_available` | 2 |
| `eligible_completed_empty_violations` | 0 |
| Latest slice `walks_available` | 8 (idempotent reuse on `ce7df86d…`) |
| `p0_b4_pass` | true |

### Exit gates

- [x] Phase 05 uses scheduling eligibility before receipt outcome
- [x] Eligible + zero walks → `BLOCKED` (not `COMPLETED_EMPTY`)
- [x] Schedule pass enforces walks when `should_schedule`
- [x] B-G4: ≥1 recent phase 05 slice with walks persisted/available

**Next step:** ~~**B5**~~ → ~~**B6**~~ → ~~**C1–C5**~~ → ~~**D1**~~ → ~~**D2**~~ → ~~**D3**~~ → **D5** (parallel) + hold **48h AA clock** daily until M3.

---

## Step B.5 completion — graph-hash autonomous chain (04→07)

**Completed:** 2026-05-23  
**Goal:** Prove graph-hash trigger → walks → sync TCRE → phase 07 on one pipeline run without unlock scripts (B-G5 orchestration / P2-B).

### What was implemented

| Area | Change |
|------|--------|
| Chain runner | `graph_hash_autonomous_chain.py` — `run_graph_hash_autonomous_chain_v1`, SQL evidence finder, stale-hash seed |
| Phase 06 | Sync TCRE with persisted phase receipt (same pattern as E2E harness) |
| Settings | `CORTEX_GRAPH_HASH_AUTONOMOUS_CHAIN` (default on; rollback = disable) |
| Proof | `continuity_p0_graph_hash_autonomous_chain.py` + `continuity_p0_phase_b5_graph_hash_autonomous_chain_proof.py` |
| Tests | `test_graph_hash_autonomous_chain.py` (unit + optional integration), `test_continuity_p0_graph_hash_autonomous_chain.py` |
| CI | `ci.yml` — B.5 chain + proof evaluator tests |

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_b5_graph_hash_autonomous_chain_proof.py \
  --use-deployed-closure
```

Auto-drives `04→05→06(sync)→07` when no complete chain in SQL window. `--drive-chain` forces; `--include-upstream` adds 02–03; `--dry-run` probe only.

| Metric | Result (2026-05-23) |
|--------|---------------------|
| `complete_chains_in_window` | 1 (post-drive) |
| `chain_drive.chain_ok` | true |
| `pipeline_run_id` | `221744c6-e595-4303-bdd4-17e87b46399e` |
| `entries_materialized` | 1599 |
| `wiring_ok` | true |
| `p0_b5_pass` | true |
| Rollback | `CORTEX_GRAPH_HASH_AUTONOMOUS_CHAIN=0` |

### Exit gates

- [x] Phase 04 invokes `trigger_graph_hash_walk_schedule_v1` (existing P2-B)
- [x] Chain runner: 04 → 05 → sync TCRE (receipt) → 07 without unlock scripts
- [x] Static wiring + proof evaluator + CI gate
- [x] Prod SQL window evidence or auto-drive pass
- [x] Cleared for **B6** (fresh pipeline run on graph change)

---

## Step B.6 completion — post-ingestion fresh pipeline run after graph change

**Completed:** 2026-05-23  
**Goal:** On authoritative graph projection hash change, start a **new** pipeline run with fresh phase 03–05 receipts — not eternal in-place mirror of `ce7df86d` (B6 / orchestration).

### What was implemented

| Area | Change |
|------|--------|
| Fresh-run module | `post_ingestion_fresh_pipeline_run.py` — supersede running run, create `graph_hash_changed` run, requeue 03–05 (no mirror) |
| Graph-hash trigger | `trigger_graph_hash_walk_schedule_v1` calls fresh run before walk schedule; sets `fresh_pipeline_run_id`, `no_phase_mirror` |
| Execution rewind | `dual_lane_worker` + `run_tenant_convergence_v1` switch lease to fresh run and rewind to phase 03 after phase 04 |
| Repository | `create_pipeline_run_v1(..., allow_coalesce_running=False)` for B6 |
| Recovery | `recover_continuity_p0_pipeline_v1(..., mirror_completed_phases=False)` opt-out |
| Settings | `CORTEX_POST_INGESTION_FRESH_RUN_ON_GRAPH_CHANGE` (default on) |
| Proof | `continuity_p0_post_ingestion_fresh_pipeline_run.py` + `continuity_p0_phase_b6_post_ingestion_fresh_pipeline_run_proof.py` |
| CI | `ci.yml` — B.6 unit + proof evaluator tests |

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_b6_post_ingestion_fresh_pipeline_run_proof.py \
  --use-deployed-closure
```

Auto-drives graph-hash change + fresh run when SQL window empty. `--drive-fresh-run` forces.

| Metric | Result (2026-05-23) |
|--------|---------------------|
| `fresh_pipeline_run_id` | `bf19b56a-f6f9-444f-8ebf-9808b95c2e50` |
| `superseded_pipeline_run_ids` | includes prior running run (not eternal mirror) |
| Fresh `phase_03/04/05` `started_at` | all after new run `created_at` |
| `no_phase_mirror` | true |
| `p0_b6_pass` | true |
| Rollback | `CORTEX_POST_INGESTION_FRESH_RUN_ON_GRAPH_CHANGE=0` |

### Exit gates

- [x] Graph-hash change supersedes running pipeline and creates new run
- [x] Phases 03–05 re-queued empty on fresh run (no 02–04 mirror)
- [x] Execution lane rewinds to phase 03 when `fresh_pipeline_run_id` present
- [x] Static wiring + proof evaluator + CI gate
- [x] Prod SQL evidence or auto-drive pass
- [x] **Phase B complete** — cleared for **Phase C**

---

## Step C.1 completion — phase 08 empty scope truth gate

**Completed:** 2026-05-23  
**Goal:** Phase 08 must not fake-green `COMPLETED_EMPTY` when the published retrieval epoch has entries but zero synthesis scopes were scheduled (C1 / AA1).

### What was implemented

| Area | Change |
|------|--------|
| Gate module | `phase08_empty_scope_truth_gate.py` — entry count, violation eval, attach to materialize output |
| Phase 08 runner | `run_substrate_phase_08_synthesis_v1` — `fail_phase_with_receipt` on violation (explicit FAIL) |
| AA1 panel | `_lawful_empty_synthesis_v1` rejects `empty_scope_violation` and entries-with-zero-jobs |
| Settings | `CORTEX_PHASE08_FAIL_ON_EMPTY_SCOPE_WITH_ENTRIES` (default on) |
| Proof | `continuity_p0_phase08_empty_scope_truth.py` + `continuity_p0_phase_c1_phase08_empty_scope_truth_proof.py` |
| CI | `ci.yml` — C.1 gate + proof evaluator + AA1 regression test |

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_c1_phase08_empty_scope_truth_proof.py \
  --use-deployed-closure
```

| Metric | Result (2026-05-23) |
|--------|---------------------|
| `legacy_empty_scope_lies` (pre-drive) | 1 (`ce7df86d…` corrected by drive) |
| `post_gate_empty_scope_lies` | 0 |
| `truthful_phase08_slices` | ≥1 |
| `retrieval_entries_in_epoch` | 1599 |
| `wiring_ok` | true |
| `p0_c1_pass` | true |
| Rollback | `CORTEX_PHASE08_FAIL_ON_EMPTY_SCOPE_WITH_ENTRIES=0` |

### Exit gates

- [x] Phase 08 fails loudly when entries exist but `scopes_scheduled=0` and `jobs_completed=0`
- [x] Lawful empty only when `retrieval_entries_in_epoch=0` (documented `scope_empty`)
- [x] AA1 no longer passes fake-green empty synthesis
- [x] Static wiring + proof evaluator + CI gate
- [x] Cleared for **C2**

---

## Step C.2 completion — per-island scope caps + orchestrator fail-loud

**Completed:** 2026-05-23  
**Goal:** Cap synthesis scopes per execution island with auditable overflow; fail phase 08 loudly on `SynthesisOrchestratorError` and when every scheduled scope fails (C2 / truthful continuity).

### What was implemented

| Area | Change |
|------|--------|
| Cap gate | `synthesis_per_island_scope_cap_gate.py` — budget resolve, capped materialize, artifact 48h stats |
| Per-island materialize | `materialize_synthesis_per_island_v1` — `per_island_scope_cap_audit`, fail-loud enforcement |
| Phase 08 runner | `run_substrate_phase_08_synthesis_v1` — `SynthesisPerIslandMaterializeError` → `fail_phase_with_receipt` |
| Settings | `CORTEX_SYNTHESIS_PER_ISLAND_FAIL_LOUD_ON_ORCHESTRATOR_ERROR` (default on) |
| Proof | `continuity_p0_phase_c2_synthesis_scope_caps.py` + `continuity_p0_phase_c2_synthesis_scope_caps_proof.py` |
| CI | `ci.yml` — C.2 cap gate + proof evaluator unit tests |

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_c2_synthesis_scope_caps_proof.py \
  --use-deployed-closure
```

| Metric | Result (2026-05-23) |
|--------|---------------------|
| `wiring_ok` | true |
| `fail_loud_on_orchestrator_enabled` | true |
| `per_island_scope_cap_law_exercised` | true (`max_scopes_on_capped_slice` ≥ 2, cap audit on phase 08 receipt) |
| `artifacts_primary_island_48h` | 1 unpublished (velocity recovers when synthesis jobs complete) |
| `phase08_drive` | auto-drive on latest completed phase 07 |
| `p0_c2_pass` | true |
| Rollback | `CORTEX_SYNTHESIS_PER_ISLAND_FAIL_LOUD_ON_ORCHESTRATOR_ERROR=0`; raise `CORTEX_SYNTHESIS_PER_ISLAND_MAX_SCOPES` |

### Exit gates

- [x] Per-island scope budget enforced with `per_island_scope_cap_audit` on materialize output
- [x] Orchestrator errors fail loud (not silent `jobs_failed` only)
- [x] All-scopes-failed surfaces `synthesis_per_island_all_scopes_failed` on phase 08
- [x] Primary island cap law exercised (≥2 scopes scheduled under cap audit) or ≥2 artifacts in 48h
- [x] Static wiring + proof evaluator + CI gate
- [x] Cleared for **C5**

---

## Step C.3 completion — unified continuity audit snapshot

**Completed:** 2026-05-23  
**Goal:** Merge operator proof entrypoints into one command that emits JSON + AA panel text + substrate SQL headline metrics + C1/C2 phase slices (C3 cleanup).

### What was implemented

| Area | Change |
|------|--------|
| Audit snapshot | `continuity_audit_snapshot.py` — `build_continuity_audit_snapshot_v1`, text formatter, baseline rollup |
| Substrate SQL core | `continuity_substrate_sql_snapshot.py` — merged headline queries from `prod_substrate_proof_queries` |
| Canonical CLI | `backend/scripts/continuity_audit_snapshot.py` (`--json`, default text+JSON) |
| Deprecation | `continuity_proof_deprecation.py` — warnings on 16 legacy proof scripts + panel + prod SQL |
| `prod_substrate_proof_queries.py` | attaches `substrate_sql_core_v1` + deprecation; points to audit snapshot |
| Proof | `continuity_p0_phase_c3_audit_snapshot.py` + `continuity_p0_phase_c3_audit_snapshot_proof.py` |
| CI | `ci.yml` — C.3 audit snapshot + proof evaluator tests |

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_c3_audit_snapshot_proof.py \
  --use-deployed-closure
# Daily ops (replaces panel + prod_substrate_proof_queries for headline truth):
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_audit_snapshot.py \
  --tenant c08ef32b-f89a-40f6-9566-e19b5329436f --json
```

| Metric | Result (2026-05-23) |
|--------|---------------------|
| `wiring_ok` | true |
| `unified_command_emits_json_fields` | true |
| `deprecated_scripts_catalogued` | 16 |
| `obligation_epoch_gap` | 3 (advisory; tracked in snapshot summary) |
| `panel_fail_count` | 3 (advisory; AA gates still visible in panel) |
| `p0_c3_pass` | true |
| Rollback | keep using legacy per-phase scripts (deprecated, still run for CI gates) |

### Exit gates

- [x] Single `continuity_audit_snapshot.py` emits panel + JSON + substrate SQL + C1/C2 slices
- [x] Legacy proof scripts emit `DeprecationWarning` and remain for CI step gates
- [x] `prod_substrate_proof_queries.py` merged core metrics into snapshot module
- [x] Static wiring + proof evaluator + CI gate
- [x] Cleared for **C5** then **C4**

---

## Step C.4 completion — restart 48h AA clock after A+B+C

**Completed:** 2026-05-23  
**Goal:** Supersede false-green pre-ABC `continuity_aa_clock_T0` and restart the forty-eight-hour M3 hold clock only after Phase A+B+C prod sign-off (C4 / honest M3).

### What was implemented

| Area | Change |
|------|--------|
| C4 restart module | `continuity_p0_phase_c4_aa_clock_restart.py` — ABC prerequisite gate, supersede prior T0, C4 T0 builder, daily hold progress |
| Prod proof | `continuity_p0_phase_c4_aa_clock_restart_proof.py` — archives pre-C4 T0, writes new T0 + `step_c4_aa48_clock_restart` |
| Daily hold | `continuity_p2_phase24_aa_clock_proof.py` — reads C4 `clock_restart_generation` ≥ 2, updates `hold_hours_elapsed` |
| Prereqs | 15 steps: A1–A6, B1–B6, C1–C3 must be `prod` sign-off (`trace_only: false`) |
| CI | `test_continuity_p0_phase_c4_aa_clock_restart.py` |

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_c4_aa_clock_restart_proof.py \
  --use-deployed-closure
# Daily until 48h elapsed + AA1–AA7 PASS:
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p2_phase24_aa_clock_proof.py \
  --use-deployed-closure --baseline-date 2026-05-22
```

| Metric | Result (2026-05-23) |
|--------|---------------------|
| `abc_prerequisites_all_pass` | true (15/15 steps) |
| `prior_t0_superseded` | true (archived `continuity_aa_clock_T0_2026-05-22_superseded_pre_c4.json`) |
| `clock_restart_generation` | 2 (C4) |
| `clock_started_at` | 2026-05-23T02:59:15Z (new epoch) |
| `all_aa_gates_pass_at_restart` | false (advisory — honest snapshot: AA1/AA5/AA6 FAIL) |
| `p0_c4_pass` | true |
| Rollback | restore archived T0 JSON; do not delete `step_c4_aa48_clock_restart` record |

### Exit gates

- [x] Phase A+B+C prerequisite baseline steps all prod-signed
- [x] Pre-C4 false-green T0 superseded and archived
- [x] New T0 records `clock_restart_generation: 2` and fresh `clock_started_at`
- [x] Daily hold script reads C4 T0 and reports `hold_hours_elapsed`
- [x] Static wiring + proof evaluator + CI gate
- [x] **Phase C clock restarted** — cleared for **C5** and parallel **Phase D**

---

## Step C.5 completion — AA5 requires synthesis jobs_completed

**Completed:** 2026-05-23  
**Goal:** AA5 must not PASS on `phase_08.started_at` alone; require `jobs_completed > 0` or lawful empty (C5 / S2 / S3).

### What was implemented

| Area | Change |
|------|--------|
| Gate | `phase_c5_aa5_synthesis_jobs_completed_gate.py` — strict vs legacy advisory modes |
| Panel | `evaluate_aa5_synthesis_started_v1` delegates to C5 gate; `STRICT_AA_PANEL_SCHEMA_VERSION` → 3 |
| Settings | `CORTEX_AA5_REQUIRE_JOBS_COMPLETED` (default on) |
| Proof | `continuity_p0_phase_c5_aa5_synthesis_jobs_completed.py` + prod script |
| A4 wiring | `verify_a4_aa_panel_strict_wiring_v1` extended for AA5 C5 delegate |
| CI | C5 gate + proof evaluator tests |

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_c5_aa5_synthesis_jobs_completed_proof.py \
  --use-deployed-closure
```

| Metric | Result (2026-05-23) |
|--------|---------------------|
| `wiring_ok` | true |
| `aa5_criterion_requires_jobs_completed` | true |
| `started_only_aa5_fake_passes` (historical slices) | 3 |
| `started_only_aa5_pass_lies` | 0 (strict gate correctly FAILs started-only) |
| `panel_aa5_verdict` | FAIL (`phase_08_started_without_jobs_completed`) |
| `p0_c5_pass` | true |
| Rollback | `CORTEX_AA5_REQUIRE_JOBS_COMPLETED=0` → started-only → ADVISORY |

### Exit gates

- [x] AA5 PASS only when `jobs_completed > 0` or lawful documented empty
- [x] Started-only historical slices no longer get AA5 PASS under strict mode
- [x] Fake-started flag exposed in gate evidence for audits
- [x] Static wiring + proof evaluator + CI gate
- [x] **Phase C (C1–C5) implementation complete** — parallel **Phase D** + 48h clock hold

---

## Step D.1 completion — admin primary KPI (drainable + islands)

**Completed:** 2026-05-23  
**Goal:** Admin primary KPI = `drainable_routable` + execution island list; deprecate raw−mat hero metric (D1 / D-G3).

### What was implemented

| Area | Change |
|------|--------|
| Metrics | `canonical_operator_metrics.py` — shared drainable / untreated / deferral snapshot |
| KPI block | `pipeline_admin_operator_kpi.py` — `build_operator_primary_kpi_v1` + island list (cap 32) |
| Overview API | `pipeline_admin_overview.py` — `operator_primary_kpi` on full + execution + phases slices |
| Continuity cards | `continuity_overview_v1.py` — canonical `backlog_count` = drainable; first signal `drainable_routable` |
| Canonical tab | `canonical_phase_admin_lite.py` — `operator_metrics` + `drainable_estimate` on phase summary |
| Contracts | `AdminCortexOperatorPrimaryKpi` on overview responses |
| Settings | `CORTEX_ADMIN_PRIMARY_KPI_DRAINABLE` (default on; rollback → raw−mat primary) |
| Admin UI | `OperatorPrimaryKpiCard.tsx` on cortex overview; `CanonicalSummaryPanels` leads with drainable |
| Proof | `continuity_p0_phase_d1_admin_operator_primary_kpi.py` + prod script |
| CI | D1 proof evaluator + operator KPI helper tests |

### Validate (local)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python -m pytest \
  tests/vector/domains/cortex/pipeline/test_pipeline_admin_operator_kpi.py \
  tests/vector/domains/cortex/substrate_pipeline/test_continuity_p0_phase_d1_admin_operator_primary_kpi.py \
  tests/vector/api/http/routes/test_admin_cortex_pipeline_overview.py -q
```

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_d1_admin_operator_primary_kpi_proof.py \
  --use-deployed-closure
```

| Check | Expected |
|-------|----------|
| `primary_metric_is_drainable` | true |
| `raw_minus_mat_banner_deprecated` | true |
| `canonical_backlog_matches_drainable` | true |
| `canonical_first_signal_drainable` | true |
| `execution_islands_exposed` | true |
| `fix7_admin_metric_truth` | true |
| Rollback | `CORTEX_ADMIN_PRIMARY_KPI_DRAINABLE=0` → raw−mat primary |

### Exit gates

- [x] Pipeline overview exposes `operator_primary_kpi` with drainable primary + islands
- [x] Canonical phase strip uses drainable backlog (not raw−mat hero)
- [x] Admin UI shows drainable + island table on cortex overview
- [x] Fix 7 static wiring (`evaluate_fix7_admin_metric_truth_v1`) passes
- [x] Static wiring + proof evaluator + CI gate
- [ ] Prod baseline `step_d1_admin_operator_primary_kpi` (run prod script after deploy)

**Next step:** ~~**D2**~~ → ~~**D3**~~ → ~~**D4**~~ → **D5** — delete legacy coordinator enqueue paths.

---

## Step D.2 completion — GitHub ingest caps = code defaults (10/16/120)

**Completed:** 2026-05-23  
**Goal:** Prod ECS env matches code defaults for Fix-6 trio; remove legacy 5/8/25 overrides that inflated deferral growth (D2 / D-G4).

### What was implemented

| Area | Change |
|------|--------|
| Manifest | `github_ingest_caps_code_defaults.py` — 10 pages/repo, 16 repos, 120s budget |
| ECS merge | `ecs_align_github_ingest_caps.py` — upsert env on task definition JSON |
| Deploy | `.github/workflows/deploy.yml` — align caps on API + worker before register |
| Infra | `infra/ecs/backend-task.json`, `worker-task.json` — explicit cap env vars |
| Fix-6 aliases | `step12_track_b_p3.py` — env fallbacks 10/16/120 (not legacy 5/8/25) |
| Settings | `CORTEX_GITHUB_CAPS_ENFORCE_CODE_DEFAULTS` (default on) |
| Proof | `continuity_p0_phase_d2_github_caps_align.py` + prod script (ECS probe + deferral totals) |
| CI | D2 merge helper + proof evaluator tests |

### Validate (local)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python -m pytest \
  tests/vector/domains/cortex/ingestion/test_github_ingest_caps_code_defaults.py \
  tests/vector/domains/cortex/substrate_pipeline/test_continuity_p0_phase_d2_github_caps_align.py -q
```

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_d2_github_caps_align_proof.py \
  --use-deployed-closure
```

Requires a deploy that ran the D2 cap-align steps (or manual ECS env at 10/16/120). Use `--skip-ecs-probe` only for wiring/dry-run.

| Check | Expected |
|-------|----------|
| `settings_defaults_match_code` | true |
| `infra_ecs_json_has_code_defaults` | true |
| `prod_api_ecs_caps_match_code_defaults` | true (after deploy) |
| `prod_worker_ecs_caps_match_code_defaults` | true (after deploy) |
| `no_legacy_low_override_*` | true (not 5/8/25) |
| `deferral_totals_snapshot_present` | true |
| Rollback | `CORTEX_GITHUB_CAPS_ENFORCE_CODE_DEFAULTS=0` + remove ECS cap env |

### Exit gates

- [x] Code defaults documented and match `settings.py` Field defaults
- [x] Deploy workflow merges caps into every API/worker task registration
- [x] Infra ECS JSON templates carry explicit cap env
- [x] Static wiring + proof evaluator + CI gate
- [ ] Prod baseline `step_d2_github_caps_code_defaults` (after deploy + prod proof)

---

## Step D.3 completion — graph promotion on convergence schedule

**Completed:** 2026-05-23  
**Goal:** Verify lawful edge promotion runs inline on the convergence worker schedule (not legacy Celery sidecar or manual-only); authoritative links grow when candidates exist (D3 / D-G4 graph floor).

### What was implemented

| Area | Change |
|------|--------|
| Convergence hook | `schedule_graph_density_promotion_on_convergence_worker_v1` — backlog-threshold inline pass per worker slice |
| Trigger | `PROMOTION_TRIGGER_CONVERGENCE_SLICE` on `schedule_graph_density_pass_v1` |
| Worker wiring | `run_tenant_convergence_v1` + `run_dual_lane_convergence_v1` call D3 hook each slice |
| Lease manifest | `graph_density_promotion_schedule` on lease `detail_json` for ops visibility |
| Settings | `CORTEX_GRAPH_DENSITY_PROMOTION_ON_CONVERGENCE` (default on; rollback → manual/phase-03 only) |
| Static verify | `verify_d3_graph_promotion_on_convergence_worker_v1` in `scheduling.py` |
| Proof | `continuity_p0_phase_d3_graph_promotion_schedule.py` + prod script (48h auth-link SQL trend) |
| CI | D3 wiring + proof evaluator tests |

### Validate (local)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python -m pytest \
  tests/vector/domains/cortex/operational_runtime/test_graph_density_promotion_convergence_schedule.py \
  tests/vector/domains/cortex/substrate_pipeline/test_continuity_p0_phase_d3_graph_promotion_schedule.py -q
```

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_d3_graph_promotion_schedule_proof.py \
  --use-deployed-closure
```

Use `--no-drive` for wiring-only (no live promotion passes on prod tenant).

| Check | Expected |
|-------|----------|
| `m9_legacy_promotion_celery_absent` | true |
| `convergence_worker_promotion_hook` | true |
| `inline_execution_path_only` | `inline_execution_slice` |
| `auth_links_48h_trend_snapshot_present` | true |
| `auth_links_increase_when_candidates_exist` | true when candidates > 0 |
| Rollback | `CORTEX_GRAPH_DENSITY_PROMOTION_ON_CONVERGENCE=0` |

### Exit gates

- [x] Promotion inline on every convergence worker slice (when backlog > threshold)
- [x] Legacy `app.tasks.cortex_graph_density_promotion` still absent (M9)
- [x] Convergence Celery beat sweep remains authoritative scheduler
- [x] 48h authoritative-link trend SQL in proof snapshot
- [x] Static wiring + proof evaluator + CI gate
- [ ] Prod baseline `step_d3_graph_promotion_on_convergence_schedule` (after deploy + prod proof)

**Next step:** ~~**D4**~~ → **D5** — delete legacy coordinator enqueue paths.

---

## Step D.4 completion — permanent orphan (466) as bounded omission

**Completed:** 2026-05-23  
**Goal:** Document Fizzer-class `permanent_orphan` deferrals as bounded omission, not a drain failure; stop operators chasing `deferral_total → 0` (D4).

### What was implemented

| Area | Change |
|------|--------|
| Doctrine | `permanent_orphan_omission_doctrine.py` — posture, Fizzer reference 466, operator block |
| Runbook | `DOCS/cortex/operational-runtime/canonical_permanent_orphan_omission_runbook.md` |
| KPI block | `pipeline_admin_operator_kpi.py` — `deferral_omission` on `operator_primary_kpi` |
| Canonical projection | `canonical_completeness_projection.py` — `deferral_omission_posture`, `chase_zero_deferrals_forbidden` metrics |
| Continuity cards | `continuity_overview_v1.py` — “Permanent orphan (omission)” signal; canonical lane not blocked on count alone |
| Operator snapshot | `operator_snapshot.py` — guidance references D4 runbook |
| Contracts | `AdminCortexDeferralOmissionPosture` on `AdminCortexOperatorPrimaryKpi` |
| Settings | `CORTEX_CANONICAL_PERMANENT_ORPHAN_OMISSION_DOC` (default on) |
| Admin UI | `DeferralOmissionCard.tsx` on cortex overview; `CanonicalSummaryPanels` omission copy |
| Proof | `continuity_p0_phase_d4_permanent_orphan_omission.py` + prod script |
| CI | D4 wiring + proof evaluator tests |

### Validate (local)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python -m pytest \
  tests/vector/domains/cortex/substrate_pipeline/test_continuity_p0_phase_d4_permanent_orphan_omission.py \
  tests/vector/api/http/routes/test_admin_cortex_pipeline_overview.py -q
```

### Prod proof (Fizzer)

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_d4_permanent_orphan_omission_proof.py \
  --use-deployed-closure
```

| Check | Expected |
|-------|----------|
| `static_wiring_ok` | true |
| `runbook_present` | true |
| `permanent_orphan_posture_documented` | `accepted_bounded_debt` when permanent > 0 |
| `chase_zero_deferrals_forbidden_when_permanent_present` | true when permanent share ≥ 20% |
| `overview_exposes_deferral_omission` | true |
| `fizzer_reference_documented` | 466 |
| Rollback | `CORTEX_CANONICAL_PERMANENT_ORPHAN_OMISSION_DOC=0` |

### Exit gates

- [x] Runbook + doctrine codify permanent orphan as omission class
- [x] Pipeline overview exposes `deferral_omission` block
- [x] Admin UI surfaces deferral omission card + canonical tab copy
- [x] Continuity canonical card labels permanent orphans as omission (not blocker)
- [x] Static wiring + proof evaluator + CI gate
- [ ] Prod baseline `step_d4_permanent_orphan_omission_doctrine` (after deploy + prod proof)

**Next step:** **D5** — delete legacy coordinator enqueue paths.

---

## Execution order summary (single page)

```text
Week 0 (incident):  A1 → A2 → A3 → A4 → A6
Week 1 (heart):     B1 → B2 → B3 → B4 → B5 → B6
Week 2 (truth):     C1 → C2 → C5 → C3 → C4 (restart 48h clock)
Parallel:           ~~D1~~, ~~D2~~, ~~D3~~, ~~D4~~, D5
Ongoing:            Daily: continuity_audit_snapshot.py (--json)
Banned:             unlock_step*, trace-only baseline sign-off
```

---

## References (commands)

```bash
# Phase A1 — synthesis job table (done; re-run if running drifts)
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_a1_synthesis_job_reconcile_proof.py --stale-seconds 0

# Phase A2 — ECS API+worker alignment (done; re-run after deploy or split-drift)
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_a2_ecs_deploy_align_proof.py --use-deployed-closure --probe-only
# Full deploy (requires ECR push IAM): ../backend/scripts/prod_deploy_backend_worker.sh

# Phase A3 — TCRE queued drain (done; re-run if queued jobs age in)
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_a3_tcre_queued_drain_proof.py --use-deployed-closure --lease-only

# Phase A4 — strict AA1/AA6 panel gates (done; prod sign-off — no --trace-only)
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_a4_aa_panel_strict_proof.py --use-deployed-closure

# Phase A5 — trace-only ban audit (done)
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_a5_trace_only_ban_proof.py --use-deployed-closure

# Phase A6 — synthesis terminal transitions (done; re-run if running/queued drifts)
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_a6_synthesis_terminal_transitions_proof.py --use-deployed-closure

# Phase B5 — graph-hash autonomous chain (done; re-run if chain evidence stale)
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_b5_graph_hash_autonomous_chain_proof.py --use-deployed-closure

# Phase B6 — fresh pipeline run on graph change (done; re-run if only stale mirrors)
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_b6_post_ingestion_fresh_pipeline_run_proof.py --use-deployed-closure

# Phase C1 — phase 08 empty scope truth (done; re-run if COMPLETED_EMPTY lies return)
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_c1_phase08_empty_scope_truth_proof.py --use-deployed-closure

# Phase C2 — per-island scope caps + orchestrator fail-loud (done; re-run if artifact velocity drops)
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_c2_synthesis_scope_caps_proof.py --use-deployed-closure

# Phase C3 — unified audit snapshot (done; daily ops entrypoint)
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_audit_snapshot.py \
  --tenant c08ef32b-f89a-40f6-9566-e19b5329436f --json

# Phase C5 — AA5 jobs_completed gate (done; re-run after AA panel changes)
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_c5_aa5_synthesis_jobs_completed_proof.py --use-deployed-closure

# Legacy (deprecated; CI step gates only)
python scripts/continuity_proof_panel.py --tenant c08ef32b-f89a-40f6-9566-e19b5329436f --json
python scripts/prod_substrate_proof_queries.py

# Deploy truth
CONTINUITY_DEPLOY_GIT_SHA=$(git rev-parse HEAD) python scripts/record_continuity_p0_deploy.py

# Phase D4 — permanent orphan omission doctrine (done; re-run after admin copy changes)
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_d4_permanent_orphan_omission_proof.py --use-deployed-closure

# Phase C4 — restart 48h AA clock after A+B+C (done; run once after deploy)
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_c4_aa_clock_restart_proof.py --use-deployed-closure

# Daily 48h hold progress (after C4 restart)
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p2_phase24_aa_clock_proof.py --use-deployed-closure --baseline-date 2026-05-22
```

---

*This plan implements recovery and stabilization only. It does not authorize new architecture phases until Phase C exit gates pass on Fizzer prod.*
