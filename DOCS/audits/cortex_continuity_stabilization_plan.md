# Cortex continuity stabilization plan

**Status:** Operational recovery plan — grounded in production reality, not architecture speculation  
**Phase A step A.1:** **Done** (2026-05-23) — see [Step A.1 completion](#step-a1-completion--synthesis-job-lifecycle)  
**Phase A step A.2:** **Done** (2026-05-23) — see [Step A.2 completion](#step-a2-completion--ecs-deploy-alignment)  
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
| **A3** | Drain stuck TCRE `queued` job | Unblocks 06→07 resume | `tcre_resume.py`, Celery task | N/A | 0 queued older than 1h | SQL + `resume_convergence_from_waiting_v1` trace | Re-queue job | **runtime** |
| **A4** | Tighten AA1 + AA6 in proof panel | Stop false M3 confidence | `continuity_proof_panel.py` | Remove mat-only AA6 fallback | AA1 FAIL on empty 08; AA6 requires delta or drainable ↓ | Unit tests + panel JSON | Revert gate logic | **ops** |
| **A5** | Ban `--trace-only` as prod sign-off | Baselines must mean something | All `continuity_p3_*_proof.py` | Document CI-only mode | Baseline updates require `trace_only: false` | Code review + baseline schema | N/A | **cleanup** |
| **A6** | Fix synthesis job terminal transitions | Prevent A1 recurrence | `synthesis_orchestrator.py` | Remove duplicate enqueue paths | 24h soak: running stable | CloudWatch + SQL cron | Revert orchestrator | **runtime** |

### Phase B — Recurrence stabilization (retrieval heartbeat)

| Step | Goal | Why | Subsystem | Remove / simplify | Success | Validate | Rollback | Type |
|------|------|-----|-----------|-------------------|---------|----------|----------|------|
| **B1** | **Single publish contract:** materialize → publish → same `index_epoch` on all new entries | Fixes B3 root cause | `retrieval_component_materialization.py`, `retrieval_index_materialization.py`, phase 07 runner | Stop publishing epoch before island mat completes | All new entries share `published_index_epoch` | SQL: epoch on entries = `get_published_index_epoch_v1` | Feature flag off island scope | **retrieval** |
| **B2** | On epoch change: re-materialize primary island OR bump `island_scope` tags | Lawful invalidation | `materialize_retrieval_index_for_pipeline_v1` | N/A | `retrieval_entries_in_scope > 0` for current epoch | Per-island count in phase 08 output | Skip re-mat (slower) | **retrieval** |
| **B3** | Wire phase 07 → registry `last_retrieval_epoch` on success | Inspect truth | `execution_island_registry.py` | Sync-on-inspect only → sync on publish | Registry epoch matches DB | `build_island_registry_inspect_v1` | Manual SQL update | **orchestration** |
| **B4** | Phase 05: require `walks_persisted > 0` when scheduling eligible | Walks drive downstream | `phase_runners` phase 05, `schedule_octs_walks` | Empty COMPLETED_EMPTY walks | Receipt shows walks_persisted ≥ 1 | Phase 05 `output_json` | Loosen threshold | **runtime** |
| **B5** | Graph-hash trigger → walk → TCRE → 07 chain (one integration test) | Proves autonomous chain | `execution_event_triggers.py`, dual-lane | Manual full slices only | End-to-end without unlock in CI | Integration test + prod SQL window | Disable trigger | **orchestration** |
| **B6** | Post-ingestion **new pipeline run** after graph change (not only recover in place) | Fresh 03/04/05 receipts | `orchestrator.py`, `start_substrate_pipeline_run_v1` | Eternal `ce7df86d` mirror | New run id OR phases 03–05 re-run timestamps | SQL phase `started_at` | Keep old run | **orchestration** |

### Phase C — Synthesis + truthful continuity

| Step | Goal | Why | Subsystem | Remove / simplify | Success | Validate | Rollback | Type |
|------|------|-----|-----------|-------------------|---------|----------|----------|------|
| **C1** | Phase 08 FAIL if scopes=0 but entries exist in epoch | Stop COMPLETED_EMPTY lie | `synthesis_pipeline.py`, `synthesis_per_island.py` | N/A | `jobs_completed ≥ 1` or explicit FAIL | Phase receipt + AA1 | Allow empty (old) | **synthesis** |
| **C2** | Cap scopes per island; fail loud on orchestrator error | Predictable cost | `synthesis_per_island.py`, settings | Unbounded retry | 2+ artifacts per 48h on primary island | `cortex_synthesis_artifacts` count | Raise caps | **synthesis** |
| **C3** | Merge proof scripts → `continuity_audit_snapshot.py` | One ops entrypoint | `backend/scripts/*proof*` | 10+ phase scripts (keep 1–2 CI) | Single command outputs JSON + panel | Doc in plan | Keep old scripts deprecated | **cleanup** |
| **C4** | Restart 48h AA clock **after** A+B+C on strict gates | Honest M3 | `continuity_p2_aa_clock.py` | Old T0 baseline | New `continuity_aa_clock_T0_*.json` | Daily `continuity_p2_phase24_aa_clock_proof.py` | N/A | **ops** |
| **C5** | AA5: require `jobs_completed > 0` not merely started | Closes fake synthesis | `continuity_proof_panel.py` | N/A | AA5 tied to S2 | Panel tests | AA5 advisory only | **ops** |

### Phase D — Canonical honesty + graph floor (parallel, non-blocking)

| Step | Goal | Why | Subsystem | Remove / simplify | Success | Validate | Rollback | Type |
|------|------|-----|-----------|-------------------|---------|----------|----------|------|
| **D1** | Admin primary KPI = `drainable_routable` + island list | Stop raw−mat hero | `pipeline_admin_overview.py`, `canonical_completeness_projection.py` | Deprecate raw−mat banner | UI shows island KPIs | Screenshot + API contract | Restore old KPI | **admin** |
| **D2** | Prod env: GitHub caps = code defaults (10/16/120…) | Slow deferral growth | `settings.py`, ECS task env | Conflicting env vars | Deferral growth rate ↓ week over week | `deferral_totals` trend | Lower caps | **ops** |
| **D3** | Promotion worker: verify Celery/inline on schedule | Graph floor for island | `graph_density_promotion` task | Manual promotion only | `auth_links` increases when candidates exist | SQL trend 48h | N/A | **graph** |
| **D4** | Document permanent orphan class (466) as omission not failure | Stops chasing 0 deferrals | Docs + admin copy | N/A | Operators accept bounded debt | Runbook | N/A | **ops** |
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
| A-G4 | Unit tests: AA1 fails on `COMPLETED_EMPTY` fixture; AA6 fails on mat-only fixture |
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

- [ ] No baseline update without `trace_only: false`
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
- [ ] A-G5 CloudWatch terminal logs (after deploy of A.1 closure SHA to ECS)

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

**Next step:** **A3** — drain stuck TCRE `queued` job.

---

## Execution order summary (single page)

```text
Week 0 (incident):  A1 → A2 → A3 → A4 → A6
Week 1 (heart):     B1 → B2 → B3 → B4 → B5
Week 2 (truth):     C1 → C2 → C5 → C3 → C4 (restart 48h clock)
Parallel:           D1, D2, D3, D5
Ongoing:            Daily: continuity_proof_panel + SQL recurrence queries
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

# Daily operator truth (after C3)
python scripts/continuity_proof_panel.py --tenant c08ef32b-f89a-40f6-9566-e19b5329436f --json
python scripts/prod_substrate_proof_queries.py   # until merged into continuity_audit_snapshot.py

# Deploy truth
CONTINUITY_DEPLOY_GIT_SHA=$(git rev-parse HEAD) python scripts/record_continuity_p0_deploy.py

# 48h clock (only after C4 restart)
python scripts/continuity_p2_phase24_aa_clock_proof.py
```

---

*This plan implements recovery and stabilization only. It does not authorize new architecture phases until Phase C exit gates pass on Fizzer prod.*
