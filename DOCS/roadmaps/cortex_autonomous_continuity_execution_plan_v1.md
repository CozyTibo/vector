# Cortex autonomous continuity — execution plan v1

**Status:** Master implementation roadmap (authoritative for engineering execution)  
**Supersedes for continuity work:** war-room “alive wedge” ordering where it conflicts with AA metrics below  
**Normative ontology:** [`DOCS/architecture/cortex_execution_reality_model_v0.md`](../architecture/cortex_execution_reality_model_v0.md)  
**Evidence inputs (do not re-audit):**

- [`DOCS/audits/cortex_post_unlock_reality_audit.md`](../audits/cortex_post_unlock_reality_audit.md)
- [`DOCS/audits/cortex_autonomous_execution_continuity_audit.md`](../audits/cortex_autonomous_execution_continuity_audit.md)
- [`DOCS/audits/cortex_execution_intelligence_unlock_master_plan.md`](../audits/cortex_execution_intelligence_unlock_master_plan.md)
- [`DOCS/audits/cortex_execution_unlock_challenge.md`](../audits/cortex_execution_unlock_challenge.md)

**North star:** Transform Cortex from **wedge-capable substrate** → **autonomously continuous execution intelligence substrate** (AA1–AA7 over 48h, not A1–A6 snapshot).

---

## 1. Executive truth

| Today | Target |
|-------|--------|
| Substrate **exists** (20k mats, 7k handles, 400 auth links) | Same substrate **evolves** without operator scripts |
| FSM **frozen** at failed phase 05 | FSM **cycles** 05→06→07→08 on post-ingestion runs |
| Traversal/retrieval/synthesis **wedge-frozen** | **Recurring** walks, index epochs, synthesis jobs |
| Global graph law **forbids** scheduling (97% orphans) | **Component-scoped** lawful walks + RET-SKIP outside scope |
| Operator metrics **fake-green** | **Continuity metrics** gate sign-off |

**Brutal honesty:** Full org-wide connected graph at Fizzer scale under current ingest caps is **not** a near-term requirement (reality model §12). **Autonomous continuity** must be defined on **execution islands** and **honest degradation**, not global ρ→1.

**Implementation thesis:** Fix **hard failures first** (P0), then **unfreeze propagation law** (P1), then **decouple canonical stress from execution lane** (P1), then **event-driven continuity** (P2).

---

## 2. Current continuity state (condensed)

Prod tenant `c08ef32b-f89a-40f6-9566-e19b5329436f` (2026-05-22):

| Layer | Substrate | Autonomous continuity |
|-------|-----------|----------------------|
| Ingest | ✓ | ✓ |
| Canonical | ✓ partial (`topology_wait`) | ✗ (`convergence_delta_succeeded=0`) |
| Identity / graph export | ✓ (once) | ✗ (no re-run) |
| Traversal | artifacts | ✗ (schema + Law P3) |
| TCRE | ✗ | ✗ |
| Retrieval | frozen 216 | ✗ |
| Synthesis | 1 wedge | ✗ |
| **AA1–AA7** | — | **0/7** |

**CONT-INV failures:** CONT-INV-01 through CONT-INV-09 (see continuity audit §1).

---

## 3. Root-cause dependency graph

```text
                    ┌─────────────────────────────┐
                    │ P0-A: OCTS schema in worker │
                    │ (CONT-INV-02)               │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │ P0-B: phase_05 COMPLETED    │
                    │ (CONT-INV-01 partial)       │
                    └──────────────┬──────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
┌────────▼────────┐    ┌───────────▼──────────┐   ┌─────────▼─────────┐
│ P1-A: component │    │ P0-C: new pipeline   │   │ P1-B: promotion   │
│ traversal law   │    │ run / recover failed │   │ worker verified   │
│ (CONT-INV-03)   │    │ run (CONT-INV-08)    │   │ (graph evolution) │
└────────┬────────┘    └───────────┬──────────┘   └─────────┬─────────┘
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │ P1-C: TCRE 06→wait→resume→07 │
                    │ (CONT-INV-04, R1)           │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │ P1-D: retrieval epoch recur.  │
                    │ (CONT-INV-05)               │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │ P1-E: phase_08 synthesis      │
                    │ (CONT-INV-06)               │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │ P2: canonical lane decoupled  │
                    │ + ingest caps (CONT-INV-07) │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │ PROOF: AA1–AA7 × 48h        │
                    └─────────────────────────────┘

Parallel track (does NOT unblock P0-A):
  canonical topology_wait / 7715 deferrals → full convergence (weeks)
```

**Rule:** No work below P0-A counts toward “autonomous continuity proven.”

---

## 4. Mandatory P0 fixes

| ID | Fix | Type | Files / deploy | Unblocks | Proof |
|----|-----|------|----------------|----------|-------|
| **P0-A** | Embed OCTS walk policy schema in **worker** (and API if workers share image) | **Mandatory** implementation | `backend/Dockerfile` COPY `DOCS/cortex/05-traversal/schemas/` **or** `walk_policy.py` package-relative schema; add test `test_walk_policy_schema_loadable_without_repo_docs` | CONT-INV-02 | Phase 05 receipt `COMPLETED`; `lease.last_error` null |
| **P0-B** | After deploy: convergence slice completes phase 05 with `walks_persisted > 0` and walk `created_at > phase_04.completed_at` | **Mandatory** operational | `run_tenant_convergence_v1`; SQL on `cortex_octs_durable_walk_records` | CONT-INV-01 | Receipt + timestamps |
| **P0-C** | Recover failed pipeline run: new `post_ingestion` run or admin recovery that resets phase 05 receipt + cursor | **Mandatory** operational | `start_substrate_pipeline_run_v1` / recovery docs; avoid eternal `faa5469f` failed mirror | CONT-INV-08 | `cortex_substrate_pipeline_runs.status` ≠ failed |
| **P0-D** | Gate CI: worker image smoke imports `validate_walk_policy_for_request_v1(SUBSTRATE_WALK_POLICY_V1)` | **Mandatory** anti-regression | `.github/workflows/*` + `tests/vector/domains/cortex/traversal/test_walk_policy_packaging.py` | CONT-INV-02 | CI green |

**Temporary (allowed only until P0-A deployed):** None for phase 05 — wedges do not fix CONT-INV-02.

**Anti-fake-green:** Do not run step 9 walk wedge as proof of P0 completion.

---

## 5. P1 continuity fixes

| ID | Fix | Type | Files | Unblocks |
|----|-----|------|-------|----------|
| **P1-A** | **Component-scoped traversal propagation** (see §8) | **Architectural** (localized law change) | `substrate_traversal_scheduling.py`, `graph_completeness_propagation.py`, tests `test_phase085_traversal_scheduling.py` | CONT-INV-03 |
| **P1-B** | Verify Celery `graph_density_promotion_pass` runs in prod; raise `cortex_graph_density_promotion_max_per_pass` until pending ≤ θ | **Operational** + settings | `app/tasks/cortex_graph_density_promotion.py`, `settings.py`, CloudWatch task metrics | Graph evolution, island growth |
| **P1-C** | **Component-scoped retrieval materialization** — bind/index per connected component above min size | **Architectural** | `retrieval/*materialization*`, skip registry docs | CONT-INV-05 |
| **P1-D** | Prove TCRE path: phase 06 → `mark_tenant_waiting_v1` → job terminal → `resume_convergence_from_waiting_v1` → phase 07 | **Mandatory** integration test + prod trace | `execution/run_tenant_execution.py`, `execution/tcre_resume.py`, `on_tcre_job_terminal_for_execution_v1` | CONT-INV-04 |
| **P1-E** | Phase 08 runs in worker after 07 policy pass | **Mandatory** path proof | `run_phase_08_synthesis_v1`, `synthesis_idle_classification.py` | CONT-INV-06 |
| **P1-F** | **Decouple lease `topology_wait` from execution lane** — see §9 FSM | **Architectural** | `run_tenant_execution.py`, `lease.detail_json` semantics | Operator clarity; optional parallel canonical lane |
| **P1-G** | Continuity metric exporter script (AA gates) | **Operational** | `backend/scripts/continuity_proof_panel.py` (new) | Proof automation |

---

## 6. P2 architecture evolution

| ID | Evolution | Rationale |
|----|-----------|-----------|
| **P2-A** | **Dual-lane convergence:** canonical drain lane (phase 02 loop) vs execution continuity lane (05–08), same lease, independent cursors in `detail_json` | Ontology §12 vs serial FSM tension |
| **P2-B** | **Event triggers:** `mark_tenant_dirty` on ingest; enqueue promotion on identity projection; enqueue walks on `graph_projection_stable_hash` change | Replace “only full slice” motion |
| **P2-C** | **Execution island registry** persisted per tenant (component id, entity ids, edge count, last_walk_at, last_retrieval_epoch) | First-class partial intelligence scope |
| **P2-D** | **Incremental synthesis** per island + global degradation brief | Avoid single monolithic “org intelligence” |
| **P2-E** | Raise GitHub ingest caps (Fix 6) + exhaust registry honesty in admin | CONT-INV-07 long-term |
| **P2-F** | Obligation-epoch monotonicity: each ingest bump schedules execution slice even if canonical lane busy | Survivability |

---

## 7. Propagation-law redesign proposals

### Laws to **preserve** (non-negotiable)

| Law | Why |
|-----|-----|
| L-AUTH | Only **authoritative** links traverse/bind (reality model §7) |
| L-SKIP | RET-SKIP when prerequisites missing — no hallucinated retrieval (§9) |
| L-TOPO | Canonical does not invent parents at synthesis/traversal time (§4) |
| L-DET | Substrate transforms deterministic; synthesis on bounded inputs only (§10–§11) |
| L-OMIT | Omission classes propagated to downstream (§12) |

### Laws to **challenge** (change in P1)

| Current law | Problem on Fizzer | Proposed law |
|-------------|-------------------|--------------|
| **P3 Global:** `orphan_disconnected > 0 && linked > 0` → no scheduling | Blocks **all** walks when 97% entities orphan but **216** linked island exists | **P3′ Component:** scheduling allowed per connected component with `|V| ≥ N_min` and `|E_auth| ≥ 1` |
| **P3 Global:** graph substrate_state `degraded` → admin “blocked” | True for global org graph; **false** for island intelligence | Report **global_degraded** + **islands_eligible_count** separately |
| **Retrieval:** implicit global disconnect RET-SKIP | Starves 216-entity island | **R′:** materialize per island; RET-SKIP only outside island scope |
| **FSM serial:** canonical `topology_wait` on lease while cursor at 05 | Misleading; 02 already passed | **F′:** `canonical_lane_state` vs `execution_lane_cursor` (§9) |

### Proposed **P3′** (code specification)

Replace `_is_traversal_propagation_blocked_v1` global boolean with:

```text
eligible_components = list_graph_connected_components_v1(...)
eligible = [c for c in components if len(c) >= MIN_COMPONENT_ENTITIES
            and component_has_authoritative_edge(c)]
should_schedule = len(eligible) > 0 AND queue_depth < threshold
blocked_globally = len(eligible) == 0 AND entity_count > 0
```

- **MIN_COMPONENT_ENTITIES:** start with `2` (config: `cortex_traversal_min_component_entities`, default 2).  
- **Global block** only when **zero** eligible components (true disconnect), not when **some** orphans exist elsewhere.

**Files:** `substrate_traversal_scheduling.py:96-109`, `evaluate_traversal_schedule_v1`, `graph_completeness_propagation.py:202-206` (manifest: `traversal_propagation_mode: global|component`).

**Mathematical note:** Global ρ≥0.3 requires ~3030 edges with current orphans — **infeasible** as P1 gate. Component law makes ρ_local on largest island the operative metric.

---

## 8. Scoped intelligence architecture proposal

### Problem

Organizational execution at Fizzer is **sparse**: 400 edges / 7286 entities. Demanding **global** continuity freezes the system; **local** continuity matches reality model §12 (partial intelligence).

### Target model: **Execution islands**

| Concept | Definition | Storage (P2) |
|---------|------------|--------------|
| **Execution island** | Maximal connected component in authoritative org graph projection | Derived via `list_graph_connected_components_v1` |
| **Island scope** | Stable id = hash(sorted entity ids)) | `detail_json` on walk/retrieval/synthesis receipts |
| **Island KPI** | `|V|`, `|E_auth|`, `last_walk_at`, `retrieval_epoch`, `synthesis_artifact_id` | Continuity panel script |

### Per-island pipeline (lawful)

```text
promotion adds edge within island
  → graph hash change for island
    → schedule walks with starts ∈ island (rank_walk_frontiers_by_density_v1 scoped)
      → TCRE jobs scoped to island walk outputs
        → retrieval materialization for island epoch
          → synthesis job per island (omission: outside_scope_entities=N)
```

### Outside island

- Entities in other components: **documented omission** (`outside_island_scope`), not silent failure.  
- RET-SKIP-GRAPH-DISCONNECTED **for cross-island queries only**, not for within-island bindings.

### Answers to design challenges

| Question | Answer |
|----------|--------|
| Should traversal freeze globally because 97% disconnected? | **No** — freeze only when **zero** eligible islands |
| Should retrieval operate on islands? | **Yes** — P1-C |
| Should synthesis be component-scoped? | **Yes** — P2-D; global brief optional |
| Is graph model sufficient? | **Yes locally**; **insufficient globally** — islands are the product unit |
| Structural ontology gap? | Add explicit **island** scope in receipts (P2-C) |

---

## 9. FSM evolution proposal

### Short-term (P1): **Split lease semantics**

| Field | Meaning |
|-------|---------|
| `phase_cursor` | Execution lane only (05–08), advances on success |
| `detail_json.canonical_lane` | `{outcome, convergence_health, drainable_estimate}` — may stay `topology_wait` |
| `detail_json.execution_lane` | `{last_phase_receipt, last_error}` |

**Change:** `mark_tenant_stalled_v1` only on **execution lane** fatal errors, not canonical topology spin (already separate return path for 02 continue).

**File:** `execution/run_tenant_execution.py`, `execution/lease.py`.

### Medium-term (P2): **Dual-lane worker**

```text
run_tenant_convergence_v1:
  if canonical_lane_owed: run_phase_02_slice (budget A)
  if execution_lane_owed: run phases from execution_cursor (budget B)
```

- Ingest bump increases `obligation_epoch`; both lanes marked dirty.  
- Phase 05 failure **does not** block canonical lane progress (CONT-INV-07 can improve in parallel).

### Long-term (P3): **Event-driven continuity** (not replace FSM)

| Event | Action |
|-------|--------|
| Ingest batch complete | `mark_tenant_dirty` + canonical lane |
| Identity projection complete | `schedule_graph_density_promotion` |
| Graph hash change | `schedule_octs_walks` per island |
| Walk terminal | enqueue TCRE |
| TCRE terminal | `resume_convergence` → retrieval slice |
| Retrieval epoch published | synthesis eligible |

**FSM remains** authoritative for **ordering legality**; **schedulers** drive **when** slices run. Serial phase order **within** execution lane preserved.

### What FSM should **not** become

- LLM-gated transitions  
- Skip authoritative law  
- “Green card” states without CONT/AA checks  

---

## 10. Continuity metrics and health laws

### Metric ladder (operator + engineering)

| Tier | Name | Definition | Fizzer today |
|------|------|------------|--------------|
| **M0** | Substrate present | CONT-INV-S1..S4 | Pass |
| **M1** | Alive snapshot (A1–A6) | Reality model §13 point-in-time | Pass (wedge) |
| **M2** | Execution slice healthy | Phase 05–08 receipts on latest run | Fail |
| **M3** | Autonomously alive (AA1–AA7) | 48h without wedge scripts | Fail |
| **M4** | Operationally healthy | AA + drainable trend + island growth | Fail |
| **M5** | Full convergence | raw≈mat, deferrals→0 | Fail (not P1 goal) |

### AA1–AA7 (autonomous alive — **sign-off gate**)

| ID | Criterion | SQL / receipt check |
|----|-----------|---------------------|
| AA1 | Phase cursor advances 05→06→07→08 without stall loop on same error | `cortex_substrate_phase_runs` + lease |
| AA2 | `traversal_propagation_blocked=false` **OR** `islands_eligible≥1` under P3′ | scheduling eval manifest |
| AA3 | `COUNT(tcre_jobs) > 0` and terminal jobs exist | `cortex_tcre_reconstruction_jobs` |
| AA4 | `COUNT(retrieval_entries)` increases across ≥2 `created_at` hours | retrieval table |
| AA5 | `phase_08.started_at IS NOT NULL` | phase runs |
| AA6 | `convergence_delta_succeeded > 0` in 24h **OR** `drainable_routable` ↓ monotonic | forward-progress |
| AA7 | No `unlock_step09/10/12` or manual `execution/restart` in window | ops log |

### Health laws (anti-confusion)

| State | Condition |
|-------|-----------|
| **Lawful degraded** | Islands exist; global ρ low; RET-SKIP outside island; synthesis partial with omissions |
| **Continuity degraded** | P3′ allows islands but AA4/AA5 not yet met |
| **Structurally blocked** | P0-A not deployed OR zero islands with auth edges |
| **Fake-green** | M1 pass but M3 fail |

---

## 11. Anti-fake-green rules

| Rule | Enforcement |
|------|-------------|
| **FG-1** | No sign-off on A1–A6 alone for continuity | AA script required |
| **FG-2** | `raw−mat` cannot be primary KPI | Admin uses `drainable_routable_estimate` |
| **FG-3** | Walk count must be post–phase 04 timestamp for AA2 | SQL timestamp gate |
| **FG-4** | `step12_pass` / `step11` green ≠ roadmap complete | Separate badge in admin |
| **FG-5** | Promotion must be worker-attributable (Celery task id in receipt) for density claims | Logs |
| **FG-6** | Single-batch retrieval (one `created_at`) ≠ recurring continuity | AA4 |
| **FG-7** | Synthesis without phase 08 receipt ≠ autonomous synthesis | AA5 |

---

## 12. Ordered implementation roadmap

### Phase 0 — Unblock execution lane (days 1–3)

| Step | Work | Owner | Done when | Status |
|------|------|-------|-----------|--------|
| 0.1 | Implement P0-A schema packaging + CI smoke | Backend | CI + staging worker walk validate | **Done** (see §Phase 0.1 completion below) |
| 0.2 | Deploy worker + API images | Ops | Prod deploy SHA recorded | **Done** (see §Phase 0.2 completion) |
| 0.3 | P0-C new pipeline run or recovery | Ops | New run id, not `failed` | **Done** (see §Phase 0.3 completion) |
| 0.4 | P0-B prod proof SQL | Ops | Phase 05 COMPLETED, walks after graph phase | **Done** (see §Phase 0.4 completion) |
| 0.5 | Document deploy SHA in `DOCS/audits/baselines/continuity_p0_<date>.json` | Eng | Artifact committed | **Done** (see §Phase 0.5 completion) |
| 0.6 | P0 sign-off gate (CONT-INV-01/02/08 + P0-D) | Eng | `step_0_6_p0_signoff` pass in baseline | **Done** (see §Phase 0.6 completion) |

#### Phase 0.1 completion (P0-A + P0-D)

Implemented **2026-05-22**:

| Deliverable | Location |
|-------------|----------|
| Bundled OCTS walk policy JSON Schema | `backend/src/vector/domains/cortex/traversal/schemas/octs-walk-policy-v1.schema.json` (copy of normative `DOCS/cortex/05-traversal/schemas/…`) |
| Schema resolution (bundled first, DOCS fallback for dev) | `walk_policy.py` — `bundled_oct_walk_policy_v1_schema_path()`, `oct_walk_policy_v1_schema_path()` |
| setuptools package data | `backend/pyproject.toml` — `vector.domains.cortex.traversal` → `schemas/*.json` |
| Docker image build gate (worker + API share image) | `backend/Dockerfile` — `RUN python -c … validate_walk_policy_for_request_v1(SUBSTRATE_WALK_POLICY_V1 …)` |
| Unit tests | `backend/tests/vector/domains/cortex/traversal/test_walk_policy_packaging.py` |

**Next step (0.2):** deploy image to prod so phase 05 can complete (P0-B proof is step 0.4).

#### Phase 0.2 completion (deploy API + worker)

Completed **2026-05-22** (GitHub Actions deploy on push to `main`):

| Item | Value |
|------|-------|
| Deploy git SHA | `0146cd05149c03a8b6e9572e1bc6739f24584b2e` |
| API ECS service | `vector-backend-service` → task def `vector-backend:149` |
| Worker ECS service | `vector-worker-service` → task def `vector-backend-worker:110` |
| ECR API image | `vector-backend:0146cd05149c03a8b6e9572e1bc6739f24584b2e` |
| ECR worker image | `vector-worker:0146cd05149c03a8b6e9572e1bc6739f24584b2e` |
| Baseline artifact | [`DOCS/audits/baselines/continuity_p0_2026-05-22.json`](../audits/baselines/continuity_p0_2026-05-22.json) |
| Ops scripts | `backend/scripts/prod_deploy_backend_worker.sh`, `backend/scripts/record_continuity_p0_deploy.py` |
| CI | `deploy.yml` — `services-stable` wait + image tag verification vs `GITHUB_SHA` |
| Worker image gate | `backend/worker.Dockerfile` — same P0-A `walk_policy_packaging_ok` build step as API |

**Next step (0.3):** recover or start pipeline run so phase 05 can execute on the new worker.

#### Phase 0.3 completion (P0-C pipeline recovery)

Executed **2026-05-22** on Fizzer prod:

| Item | Value |
|------|-------|
| Strategy | `new_run` — post-ingestion run with mirrored 02–04 receipts |
| New pipeline run | `ce7df86d-b229-4467-ad28-1109ed119d34` (`status=running`) |
| Prior failed run (unchanged) | `faa5469f-849b-4e19-bc26-e9ec001e926f` (`status=failed`) |
| Lease | `dirty`, `fsm_state=TRAVERSAL`, `phase_cursor=phase_05_traversal`, `obligation_epoch=777` |
| Phase 05–08 | `queued` (05 reset; no schema error in receipt) |
| Code | `continuity_p0_recovery.py`, `continuity_p0_recover_pipeline.py`, admin `POST …/execution/continuity-p0-recover` |
| Prod script | `python backend/scripts/continuity_p0_recover_pipeline.py --strategy new_run --db-only` |
| Baseline | [`continuity_p0_2026-05-22.json`](../audits/baselines/continuity_p0_2026-05-22.json) → `step_0_3_pipeline_recovery` |

Execution slice enqueue uses prod **convergence sweeper** when `--db-only` (no local Redis); worker picks up dirty lease within ~2 minutes.

**Next step (0.4):** prove phase 05 `COMPLETED` with walks after phase 04 timestamp (P0-B).

#### Phase 0.4 completion (P0-B phase 05 autonomous proof)

Executed **2026-05-22** on Fizzer prod (`c08ef32b-f89a-40f6-9566-e19b5329436f`):

| Item | Value |
|------|-------|
| Pipeline run | `ce7df86d-b229-4467-ad28-1109ed119d34` (`status=running`) |
| Phase 05 | `completed` at `2026-05-22T21:52:09Z` (receipt `COMPLETED_EMPTY`; slice had no new walks this run) |
| Walks after phase 04 | 8 rows with `created_at > phase_04.completed_at` (newest `2026-05-22T21:36:24Z`) |
| Lease | `waiting`, `fsm_state=AWAITING_TCRE`, `phase_cursor=phase_07_retrieval`, `last_error` null |
| CONT-INV-01 | Phase 05 receipt on active run — no schema-path failure |
| CONT-INV-02 | `lease.last_error` clear; no `octs-walk-policy-v1.schema.json` / DOCS path errors |
| Code | `continuity_p0_phase05_proof.py`, `continuity_p0_phase05_proof.py` (script), admin `GET …/execution/continuity-p0-phase05-proof` |
| Prod script | `python backend/scripts/continuity_p0_phase05_proof.py` (`--proof-only` to re-evaluate without slices) |
| Baseline | [`continuity_p0_2026-05-22.json`](../audits/baselines/continuity_p0_2026-05-22.json) → `step_0_4_phase05_proof` |

#### Phase 0.5 completion (baseline closure artifact)

Executed **2026-05-22** after steps 0.1–0.4:

| Item | Value |
|------|-------|
| Closure git SHA | `b8ca0065f68eaab6ce7f04749d9818c14b7ce995` |
| API ECS image | `vector-backend:b8ca0065f68eaab6ce7f04749d9818c14b7ce995` (task def `:152`) |
| Worker ECS image | `vector-worker:b8ca0065f68eaab6ce7f04749d9818c14b7ce995` (task def `:113`) |
| Prerequisites | `step_02_artifact_present`, `step_03_pass`, `step_04_pass` all true |
| Baseline | [`continuity_p0_2026-05-22.json`](../audits/baselines/continuity_p0_2026-05-22.json) → `step_0_5_phase0_closure`, `phase0_closure_git_sha`, `phase0_complete: true` |
| Code | `continuity_p0_baseline.py`, `continuity_p0_phase0_closure.py`; `record_continuity_p0_deploy.py` merge-safe |
| Prod script | `python backend/scripts/continuity_p0_phase0_closure.py --wait-for-deploy 600` |

#### Phase 0.6 completion (P0 sign-off gate)

Executed **2026-05-22** on Fizzer prod:

| Item | Value |
|------|-------|
| Gate | CONT-INV-01, CONT-INV-02, CONT-INV-08 + P0-D CI packaging |
| Pipeline run | `ce7df86d-b229-4467-ad28-1109ed119d34` (`status=running` after in-place recovery from `phase_06_tcre`) |
| Closure SHA | `6b75776d7cd0825a6b699898bb8e6e295643378a` (API + worker aligned) |
| P0-D | `deploy.yml` walk-policy test + Dockerfile/worker gates + bundled schema |
| Baseline | [`continuity_p0_2026-05-22.json`](../audits/baselines/continuity_p0_2026-05-22.json) → `step_0_6_p0_signoff`, `phase_0_signed_off: true` |
| Code | `continuity_p0_signoff.py`, `continuity_p0_phase0_signoff.py`, admin `GET …/execution/continuity-p0-signoff` |
| Prod script | `python backend/scripts/continuity_p0_phase0_signoff.py` |
| Recovery (CONT-INV-08) | `continuity_p0_recover_pipeline.py --strategy recover_in_place --resume-from-phase phase_06_tcre` |

**Phase 0 signed off.** Next: Phase 1.1 (P3′ component scheduling).

### Phase 1 — Propagation + downstream continuity (days 4–10)

| Step | Work | Done when |
|------|------|-----------|
| 1.1 | Implement P3′ component scheduling (P1-A) + unit tests | `evaluate_traversal_schedule` eligible with Fizzer islands | **Done** (see §Phase 1.1 completion) |
| 1.2 | Deploy P3′ | New walks without manual step 9 | **Done** (see §Phase 1.2 completion) |
| 1.3 | P1-B verify promotion Celery + raise caps | `pending_candidates` trending down | **Done** (see §Phase 1.3 completion) |
| 1.4 | P1-D TCRE integration test in CI | Test green | **Done** (see §Phase 1.4 completion) |
| 1.5 | P1-D/E prod: 06 waiting → resume → 07 → 08 | Phase receipts + TCRE count > 0 | **Done** (see §Phase 1.5 completion) |
| 1.6 | P1-C retrieval per island (minimal: largest island only) | AA4 partial | **Done** (see §Phase 1.6 completion) |

#### Phase 1.1 completion (P3′ component-scoped propagation)

Implemented **2026-05-22** (P1-A / CONT-INV-03 partial):

| Item | Value |
|------|-------|
| Law | P3′ replaces global orphan-disconnect block when `CORTEX_TRAVERSAL_COMPONENT_SCHEDULE` ≠ 0 |
| Settings | `cortex_traversal_component_schedule_enabled`, `cortex_traversal_min_component_entities` (default 2) |
| Scheduling | `evaluate_traversal_propagation_v1`, `list_eligible_traversal_components_v1` in `substrate_traversal_scheduling.py` |
| Propagation manifest | `traversal_propagation_mode`, `islands_eligible_count`, `global_degraded` in `graph_completeness_propagation.py` |
| Fizzer prod | `islands_eligible_count=2`, `traversal_propagation_blocked=false`, `should_schedule=true` |
| Baseline | [`continuity_p0_2026-05-22.json`](../audits/baselines/continuity_p0_2026-05-22.json) → `step_1_1_p3_component_scheduling` |
| Tests | `test_p3_component_traversal_propagation.py` + updated phase085 scheduling/propagation tests |
| Prod script | `python backend/scripts/continuity_p1_component_scheduling_proof.py` |

**Next step:** Phase 2 — synthesis / retrieval starvation unlock (see Phase 2 table).

#### Phase 1.6 completion (P1-C retrieval per largest island)

Executed **2026-05-22** on Fizzer prod:

| Item | Value |
|------|-------|
| Law | P1-C scopes `materialize_retrieval_index_for_pipeline_v1` to largest eligible island when `CORTEX_RETRIEVAL_COMPONENT_SCOPE` ≠ 0 |
| Settings | `cortex_retrieval_component_scope_enabled`, `cortex_retrieval_min_component_entities` (default 2) |
| Materialization | `retrieval_propagation_mode=component`, `island_scope_id=d7e41b3c763d38e9`, `entries_materialized=1599`, epoch `PUBLISHED` |
| Island | 257 entities; 2 eligible islands; `outside_island_scope_entity_count=7029` |
| AA4 partial | 1100 island-scoped `retrieval_entries` in 1 UTC hour bucket (advisory: multi-hour spread pending) |
| Baseline | [`continuity_p0_2026-05-22.json`](../audits/baselines/continuity_p0_2026-05-22.json) → `step_1_6_p1c_retrieval_island` |
| Code | `retrieval_component_materialization.py`, `continuity_p1_retrieval.py`, binding `omission_summary` passthrough |
| Tests | `test_continuity_p1_retrieval.py`, `test_p1c_retrieval_component_materialization.py` |
| Prod script | `python backend/scripts/continuity_p1_phase16_retrieval_proof.py --trace-only` |

#### Phase 1.5 completion (P1-D/E downstream chain — prod)

Executed **2026-05-22** on Fizzer prod:

| Item | Value |
|------|-------|
| Pipeline run | `ce7df86d-b229-4467-ad28-1109ed119d34` |
| TCRE | 3 jobs completed inline (`parent_artifact_ids` sort fix); resume via `resume_convergence_from_waiting_v1` |
| Phase 06/07 | `completed` with execution receipts |
| Phase 08 | Executed with receipt (`failed` — all scoped synthesis jobs errored; see `checks_advisory`) |
| Baseline | [`continuity_p0_2026-05-22.json`](../audits/baselines/continuity_p0_2026-05-22.json) → `step_1_5_p1de_downstream` |
| Code | `continuity_p1_downstream.py`, `edge_expansion_runtime.py` (TCRE edge sort), `test_continuity_p1_downstream.py` |
| Prod script | `python backend/scripts/continuity_p1_phase15_downstream_proof.py --wait-for-deploy 600` |

#### Phase 1.2 completion (P3′ deploy + autonomous walks)

Executed **2026-05-22** on Fizzer prod:

| Item | Value |
|------|-------|
| Closure git SHA | `80aea87620d0c81bbe648bcf9e9981a989cc11a7` (P3′ from step 1.1) |
| API ECS image | `vector-backend:80aea87620d0…` (task def `:155`) |
| Worker ECS image | `vector-worker:80aea87620d0…` (task def `:116`) |
| Schedule pass | `schedule_octs_walks_for_tenant_v1` / `after_phase_05`, `path=inline_execution_slice` |
| Autonomous walks | `walks_persisted=2` (`5872ded0…`, `175b774a…`); no `unlock_step09_graph_octs_walk.py` |
| Walk delta | 24 → 26 rows; newest `2026-05-22T22:08:19Z` (after deploy window) |
| Baseline | [`continuity_p0_2026-05-22.json`](../audits/baselines/continuity_p0_2026-05-22.json) → `step_1_2_p3_deploy`, `p1_2_closure_git_sha` |
| Code | `continuity_p1_p3_deploy.py`, `test_continuity_p1_p3_deploy.py` |
| Prod script | `python backend/scripts/continuity_p1_phase12_deploy_proof.py --wait-for-deploy 600` |

#### Phase 1.3 completion (P1-B promotion worker + caps)

Executed **2026-05-22** on Fizzer prod:

| Item | Value |
|------|-------|
| Closure git SHA | `04993e9` (promotion cap default 400) |
| Worker path (M9) | Inline `schedule_graph_density_promotion_after_identity_substrate_v1` after phase 03; legacy `app.tasks.cortex_graph_density_promotion` absent |
| Cap raised | `cortex_graph_density_promotion_max_per_pass` default **400** (`CORTEX_GRAPH_DENSITY_PROMOTION_MAX_PER_PASS`) |
| Drain proof | 3 passes × 400 promoted; `pending_link_candidates` **3600 → 2400**; auth edges **400 → 1600** |
| Baseline | [`continuity_p0_2026-05-22.json`](../audits/baselines/continuity_p0_2026-05-22.json) → `step_1_3_p1b_promotion`, `p1_3_closure_git_sha` |
| Code | `continuity_p1_promotion.py`, `test_continuity_p1_promotion.py` |
| Prod script | `python backend/scripts/continuity_p1_phase13_promotion_proof.py --wait-for-deploy 600` |

#### Phase 1.4 completion (P1-D TCRE resume — CI + prod trace)

Executed **2026-05-22** on Fizzer prod:

| Item | Value |
|------|-------|
| Closure git SHA | `1c66058` |
| Path | Phase 06 → `mark_tenant_waiting_v1` → TCRE Celery `run_tcre_reconstruction_job_task` terminal → `on_tcre_job_terminal_for_execution_v1` → `resume_convergence_from_waiting_v1` @ `phase_07_retrieval` |
| Prod trace | Pipeline `ce7df86d…`: phase 06 `completed` + `async` job `45723fb5…`; lease `waiting_reason=tcre_async`, cursor `phase_08_synthesis`; 3 TCRE jobs |
| CI gate | `deploy.yml` runs `test_continuity_p1_tcre_resume.py` + TCRE boundary tests (no DB) |
| Integration | `test_p1_d_phase06_waiting_tcre_terminal_resumes_phase07` (`@pytest.mark.integration`) |
| Baseline | [`continuity_p0_2026-05-22.json`](../audits/baselines/continuity_p0_2026-05-22.json) → `step_1_4_p1d_tcre_resume` |
| Code | `continuity_p1_tcre.py`, `test_continuity_p1_tcre_resume.py` |
| Prod script | `python backend/scripts/continuity_p1_phase14_tcre_proof.py --wait-for-deploy 600` |

#### Phase 1.5 completion (P1-D/E downstream chain — prod)

Executed **2026-05-22** on Fizzer prod:

| Item | Value |
|------|-------|
| Pipeline run | `ce7df86d-b229-4467-ad28-1109ed119d34` |
| Chain | TCRE queued jobs drained inline → `on_tcre_job_completed` resume → `run_tenant_convergence_v1` slices for phase 07 + 08 |
| Done when | Phase **06/07** `completed` + **08** execution receipt; `tcre_jobs_completed` > 0 (08 synthesis jobs on Fizzer: advisory `checks_advisory`) |
| Baseline | [`continuity_p0_2026-05-22.json`](../audits/baselines/continuity_p0_2026-05-22.json) → `step_1_5_p1de_downstream` |
| Code | `continuity_p1_downstream.py`, `test_continuity_p1_downstream.py` |
| Prod script | `python backend/scripts/continuity_p1_phase15_downstream_proof.py --wait-for-deploy 600` |

### Phase 2 — Decouple + proof panel (days 11–18)

| Step | Work | Done when |
|------|------|-----------|
| 2.1 | P1-F lease dual-lane fields | Admin/inspect shows both lanes |
| 2.2 | `continuity_proof_panel.py` | Single command prints AA1–AA7 |
| 2.3 | P2-A dual-lane worker (canonical + execution budgets) | Canonical progress while 05–08 runs |
| 2.4 | Start 48h AA clock | T0 baseline JSON |

### Phase 3 — Architecture hardening (weeks 3–6)

| Step | Work |
|------|------|
| 3.1 | P2-C island registry |
| 3.2 | P2-B event triggers (hash-change walk schedule) |
| 3.3 | P2-D per-island synthesis |
| 3.4 | P2-E ingest caps + deferral release monitoring |

---

## 13. Validation and proof strategy

### Per-PR gates

| PR contains | Required tests |
|-------------|----------------|
| walk_policy / Dockerfile | `test_walk_policy_packaging`, phase 05 integration |
| P3′ scheduling | `test_phase085_traversal_scheduling` + manifest snapshot |
| FSM lease | `test_execution_path_telemetry`, stall recovery |
| TCRE resume | existing `test_phase085_*` + new resume e2e |

### Prod proof commands (Fizzer)

```bash
cd backend
# After deploy (step 0.2):
CONTINUITY_DEPLOY_GIT_SHA=$(git rev-parse HEAD) python scripts/record_continuity_p0_deploy.py
# Phase 0 closure (step 0.5 — merges baseline, verifies ECS + prerequisites):
python scripts/continuity_p0_phase0_closure.py --wait-for-deploy 600
# Phase 0 sign-off (step 0.6 — P0 invariants + P0-D + baseline consolidation):
python scripts/continuity_p0_phase0_signoff.py
# P3′ component scheduling proof (step 1.1):
python scripts/continuity_p1_component_scheduling_proof.py
# P3′ deploy + autonomous walk proof (step 1.2):
python scripts/continuity_p1_phase12_deploy_proof.py --wait-for-deploy 600
# P1-B promotion worker + pending drain proof (step 1.3):
python scripts/continuity_p1_phase13_promotion_proof.py --wait-for-deploy 600
# P1-D TCRE resume CI boundaries + prod trace (step 1.4):
python scripts/continuity_p1_phase14_tcre_proof.py --wait-for-deploy 600
# P1-D/E downstream 06→07→08 proof (step 1.5):
python scripts/continuity_p1_phase15_downstream_proof.py --wait-for-deploy 600
# After pipeline recovery (step 0.3):
python scripts/continuity_p0_recover_pipeline.py --strategy new_run --db-only
python scripts/prod_substrate_proof_queries.py --out ../DOCS/audits/baselines/continuity_<date>.json
python scripts/continuity_proof_panel.py --tenant c08ef32b-f89a-40f6-9566-e19b5329436f  # after P1-G
```

### Sign-off checklist (M3)

- [ ] AA1–AA7 green for 48h consecutive  
- [ ] CONT-INV-01..06 pass at end of window  
- [ ] No wedge scripts in ops log  
- [ ] `continuity_<date>.json` shows `islands_eligible >= 1`, `tcre_jobs > 0`, retrieval `max(created_at) - min(created_at) > 1h`

---

## 14. Rollback and survivability strategy

| Change | Rollback | Survivability if rolled back |
|--------|----------|------------------------------|
| P0-A schema in image | Revert image tag | Phase 05 fails again (known state) |
| P3′ component law | Feature flag `CORTEX_TRAVERSAL_COMPONENT_SCHEDULE=0` → old global law | Scheduling stops; substrate intact |
| Dual-lane FSM | Flag `CORTEX_EXECUTION_DUAL_LANE=0` | Serial behavior |
| Promotion cap raise | Lower settings | Slower island growth only |

**Survivability guarantees (must hold after P0):**

| Stress | Expected behavior |
|--------|-------------------|
| Connector outage | Ingest pauses; lease dirty; no corrupt mats |
| Delayed ingestion | Deferrals grow; canonical lane `topology_wait`; execution lane can still run if islands exist |
| Missing parents | Permanent orphan class; omission documented |
| Partial replay | Deterministic receipts unchanged |
| Worker crash mid-05 | Stall + retry; no silent skip to 08 |

---

## 15. What “autonomously alive” means operationally

**Autonomously alive** = **M3**: AA1–AA7 satisfied for **48 hours** on tenant T without manual unlock scripts.

**Not:**

- Level 6 one-shot synthesis  
- 16 walks from step 9  
- Admin pipeline overview green  
- `raw−mat` decreasing  

**Operator runbook (one line):** Run `continuity_proof_panel.py`; if AA1–AA7 all PASS and FG rules satisfied, tenant is autonomously alive.

---

## 16. Final target architecture

```text
                    ┌──────────────────────┐
                    │  Operational exhaust  │
                    │  (ingest, windowed)   │
                    └──────────┬───────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
    ┌─────────▼─────────┐           ┌──────────▼──────────┐
    │ Canonical lane     │           │ Execution lane       │
    │ (deferral-aware    │           │ (FSM 05→06→07→08)     │
    │  drain, topology)  │           │                      │
    └─────────┬─────────┘           └──────────┬──────────┘
              │                                 │
              └────────────────┬────────────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Identity + promotion  │
                    │ (continuous Celery)     │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Execution islands     │
                    │ (connected components)│
                    └──────────┬───────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
 ┌───────▼──────┐    ┌─────────▼────────┐   ┌────────▼────────┐
 │ OCTS walks    │    │ TCRE per island  │   │ Retrieval epoch │
 │ per island    │    │                  │   │ per island      │
 └───────┬──────┘    └─────────┬────────┘   └────────┬────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Synthesis (LLM)       │
                    │ per island + omissions│
                    │ evidence-reducible    │
                    └──────────────────────┘
```

### Deterministic vs LLM

| Deterministic (must stay) | LLM-allowed |
|---------------------------|-------------|
| Ingest, canonical, identity, promotion, walks, TCRE bindings, RET-SKIP, receipts, epochs | Synthesis narrative on bounded retrieval bundles only |
| Island detection, metrics, FSM transitions | Nothing else |

### Success criterion (v1 product)

> A tenant accumulates **lawful execution intelligence** on **growing execution islands** over time, with **explicit omissions** for the rest of the org graph, without operator wedges — measured by **AA1–AA7**.

---

## Appendix A — Fix classification matrix

| Fix | Mandatory | Temporary | Architectural | Operational | Anti-fake-green |
|-----|-----------|-----------|---------------|-------------|-----------------|
| P0-A schema | ✓ | | | deploy | ✓ CI |
| P0-C run recovery | ✓ | | | ✓ | |
| P1-A P3′ | ✓ | | ✓ | | ✓ |
| P1-B promotion | | | | ✓ | ✓ FG-5 |
| P1-F dual-lane | | | ✓ | | ✓ FG-4 |
| P2 dual-lane worker | | | ✓ | | |
| GitHub caps | | | | ✓ | |
| Admin UI polish | | | | | **out of scope** |

## Appendix B — Continuity unlock by layer

| Layer | P0 | P1 | P2 |
|-------|----|----|-----|
| Substrate | schema (worker boot) | dual-lane canonical | ingest caps |
| Graph | — | promotion + P3′ | island registry |
| Traversal | phase 05 runs | component schedule | hash-triggered walks |
| Retrieval | — | island materialize | epoch recurrence |
| Synthesis | — | phase 08 path | per-island jobs |
| FSM | recover run | split lease semantics | event-driven |

## Appendix C — Implementation tickets (suggested)

| Ticket | Title | Priority |
|--------|-------|----------|
| CORTEX-CONT-001 | Package OCTS walk policy schema in worker image | P0 |
| CORTEX-CONT-002 | Component-scoped traversal scheduling (P3′) | P1 |
| CORTEX-CONT-003 | Island-scoped retrieval materialization v1 | P1 |
| CORTEX-CONT-004 | TCRE resume e2e + prod trace checklist | P1 |
| CORTEX-CONT-005 | Dual-lane lease + worker budgets | P2 |
| CORTEX-CONT-006 | continuity_proof_panel.py + AA baselines | P1 |
| CORTEX-CONT-007 | Celery promotion prod verification | P1 |
| CORTEX-CONT-008 | P0-C pipeline recovery (`continuity_p0_recovery`) | P0 |

---

*v1 — Update only via explicit version bump when AA sign-off or architecture pivot occurs.*
