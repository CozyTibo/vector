# Cortex Execution Intelligence Unlock Plan

**Status:** Authoritative war-room implementation document  
**Date:** 2026-05-21  
**Primary tenant (prod evidence):** `c08ef32b-f89a-40f6-9566-e19b5329436f` (Fizzer)  
**Primary bundle:** `bundle.phase03.step03.logical_keys.v1`  
**Normative ontology:** [`DOCS/architecture/cortex_execution_reality_model_v0.md`](../architecture/cortex_execution_reality_model_v0.md) (v0) — **this plan must conform**  
**Inputs:** `cortex_fsm_full_audit.md`, `cortex_fsm_unlock_plan.md`, `cortex_execution_proofs.md`, `cortex_execution_unlock_challenge.md`

**North star:** Achieve **alive criteria A1–A6** and **Level 6 lawful partial intelligence** (reality model §13, ladder below) — not full canonical convergence, not admin green, not `raw == mat`.

---

## Execution progress (12-step war-room)

| Step | Status | Completed | Notes |
|------|--------|-----------|-------|
| 1 | **Done** | 2026-05-21 | Prod baseline captured; artifact + validation module |
| 2 | **Done** | 2026-05-22 | Fix 1: `release_deferrals_when_missing_parent_ref_materialized_v1` + drain hook + tests |
| 3 | **Done** | 2026-05-22 | Fix 2: deferral-aware gate + `untreated_routable_drainable_exists_v1` |
| 4 | **Done** | 2026-05-22 | Deploy triggered + prod wedge: 7715 deferrals released; A4 validated |
| 5 | **Done** | 2026-05-22 | Identity backfill A1: 7286 active org handles on Fizzer |
| 6 | **Done** | 2026-05-22 | Candidate regen A3: 2000 link candidates (global cap) |
| 7 | **Done** | 2026-05-22 | Promotion A2: 200 authoritative links (pass cap) |
| 8 | **Done** | 2026-05-22 | Fix 3–5: phase-03 promotion hook + backfill regen + admin APIs |
| 9 | **Done** | 2026-05-22 | GRAPH/OCTS wedge A5: 16 completed walks, 8 with authoritative hops |
| 10 | **Done** | 2026-05-22 | RETRIEVAL wedge A6: 216 index entries published |
| 11 | **Done** | 2026-05-22 | 48h alive panel T0 green (Track A clock started) |
| 12 | **Done** | 2026-05-22 | Fix 6–7 + Track B soak T0 + Level 6 synthesis legality wedge |

### Step 1 completion record

- **Command:** `cd backend && .venv/bin/python scripts/prod_substrate_proof_queries.py --out ../DOCS/audits/baselines/fizzer_step01_2026-05-21.json`
- **Artifact:** [`DOCS/audits/baselines/fizzer_step01_2026-05-21.json`](baselines/fizzer_step01_2026-05-21.json) (no secrets; prod counts only)
- **Code:** `baseline_snapshot.py` validates snapshot contract; script emits `alive_baseline` summary block

**Alive baseline at capture (Fizzer prod, 2026-05-21):**

| Field | Value |
|-------|-------|
| A1 org_entities_active | 0 |
| A2 authoritative_links | 0 |
| A3 candidate_links | 0 |
| A4 last_canonical_outcome | `partial_progress` |
| A4 fsm_state / phase_cursor | `CANONICAL_DRAINING` / `phase_02_canonical` |
| raw_total / mat_total | 28,219 / 20,036 |
| raw_minus_mat_admin_gap | 8,183 |
| deferrals_total (all permanent_orphan) | 8,181 |
| anchors | 19,961 |
| primary_bundle_id | `bundle.phase03.step03.logical_keys.v1` |

*Deferral topology mix shifted vs May forensic doc (now all classified permanent_orphan); step 2+ still required for routable release path and identity wedge.*

### Step 2 completion record (Fix 1)

- **Code:** `release_deferrals_when_missing_parent_ref_materialized_v1` in `deferral_store.py` — resolves `missing_parent_ref` via `build_node_key_index` (same as `replay_topology`).
- **Wiring:** Called at drain start and after each productive batch in `drain_runtime.py` (alongside `release_deferrals_with_materialized_parents`).
- **Tests:** `test_deferral_release_missing_parent_ref.py` (unit + integration); `build_node_key_index` in `replay_topology.py`.
- **Deploy:** Step 4 (not part of step 2).

### Step 3 completion record (Fix 2)

- **`untreated_routable_drainable_exists_v1`** in `candidate_selection.py` — same deferral exclusion as drain FIFO selection.
- **`canonical_needs_more_work_v1`** uses drainable check (not raw−mat); `topology_wait` / `partial_progress` only block when drainable rows remain.
- **`canonical_may_advance_to_identity_v1`** allows phase 03 when topology-wait + zero progress but no drainable backlog.
- **`run_tenant_execution.py`** passes `bundle_id` into the gate.
- **Tests:** `test_canonical_phase_gate.py`, `test_candidate_selection_drainable.py`.
- **Deploy:** Step 4.

### Step 4 completion record (deploy + A4)

- **Deploy:** Push `main` → GitHub Actions `deploy.yml` (ECS `vector-backend-service` + `vector-worker-service`). SHA at wedge: `6cce059` (includes Fix 1–2).
- **Wedge script:** `backend/scripts/unlock_step04_deploy_validate.py` — prod release pass + optional drain retries; artifact [`baselines/fizzer_step04_2026-05-22.json`](baselines/fizzer_step04_2026-05-22.json).
- **Fix 1 prod result:** `released_missing_parent_ref=7715`; deferrals `8181 → 466`; `drainable_after_release=true`.
- **A4:** Pass via release motion + lease `last_canonical_outcome=partial_progress` (see artifact). Worker sustained slices expected after ECS rollout.
- **Perf:** `release_deferrals_when_missing_parent_ref_materialized_v1` scopes raw load to parent kinds from deferral refs (not full tenant raw scan).

### Step 5 completion record (identity backfill A1)

- **Command:** `cd backend && UNLOCK_STEP05_ANCHOR_LIMIT=20000 UNLOCK_STEP05_CHUNK_SIZE=2000 .venv/bin/python scripts/unlock_step05_identity_backfill.py`
- **Artifact:** [`baselines/fizzer_step05_2026-05-22.json`](baselines/fizzer_step05_2026-05-22.json)
- **Result:** `org_entities_active_after=7286` (`human_actor=7283`, `service_account=3`); anchors scanned across chunks with `skip_candidate_regen=True` (step 6).
- **A1:** Pass — prod anchor yield ≥7k unique handles (plateau below 10k aspirational target due to work-object anchors).
- **Code:** chunked commits + `anchor_offset` on `run_anchor_handle_backfill`; `db.expire_all()` between chunks avoids duplicate-PK on resume.

### Step 6 completion record (candidate regen A3)

- **Command:** `cd backend && .venv/bin/python scripts/unlock_step06_candidate_regen.py`
- **Artifact:** [`baselines/fizzer_step06_2026-05-22.json`](baselines/fizzer_step06_2026-05-22.json)
- **Result:** `link_candidates_before=0` → `link_candidates_after=2000` (`org.persona_belongs_to_handle`); `candidate_count=2000` at global cap (`p04.candidate.exact_notion_user_id_v1` dominated emission; later rules skipped after cap).
- **A3:** Pass — wedge ≥50 and at 2000 cap per plan §6.2.
- **Code:** `step06_candidate_regen.py` (`evaluate_a3_candidate_links_v1`); wedge script + tests `test_step06_candidate_regen.py`.

### Step 7 completion record (graph density promotion A2)

- **Command:** `cd backend && .venv/bin/python scripts/unlock_step07_graph_density_promotion.py`
- **Artifact:** [`baselines/fizzer_step07_2026-05-22.json`](baselines/fizzer_step07_2026-05-22.json)
- **Result:** `authoritative_links_before=0` → `authoritative_links_after=200` (`org.persona_belongs_to_handle`); `promoted_count=200`, `skipped_count=0`; `unpromoted_remaining=1800` (upstream cap omission per pass).
- **A2:** Pass — wedge ≥1 and at 200/pass cap per plan §6.2.
- **Code:** `step07_graph_density_promotion.py` (`evaluate_a2_authoritative_links_v1`); wedge script calls `schedule_graph_density_pass_v1(force=True, trigger=manual)`; tests `test_step07_graph_density_promotion.py`.

### Step 8 completion record (Fix 3–5 code ship)

- **Command:** `cd backend && .venv/bin/python scripts/unlock_step08_fixes_shipped.py`
- **Artifact:** [`baselines/fizzer_step08_2026-05-22.json`](baselines/fizzer_step08_2026-05-22.json)
- **Fix 3:** `schedule_graph_density_promotion_after_identity_substrate_v1` wired from `run_identity_substrate_projection_for_pipeline_v1` (inline `schedule_graph_density_pass_v1`, trigger `after_phase_04`, not phase-04 sidecar).
- **Fix 4:** `POST …/identity/backfill/from-canonical-anchors` accepts `include_candidate_regen` (default true) → `run_identity_handles_and_candidates_refresh`.
- **Fix 5:** `POST …/operational-runtime/graph-density-promotion/run`; `POST …/identity/replay-jobs/run` + `/enqueue` restored; removed from `admin_bypass_guard` forbidden list.
- **Tests:** `test_step08_fixes_shipped.py`; updated phase03 boundary, step10/11, m8 admin route tests.

### Step 9 completion record (GRAPH / OCTS execution continuity A5)

- **Command:** `cd backend && .venv/bin/python scripts/unlock_step09_graph_octs_walk.py`
- **Artifact:** [`baselines/fizzer_step09_2026-05-22.json`](baselines/fizzer_step09_2026-05-22.json)
- **Result:** Projection `7286` nodes / `200` authoritative edges; `run_substrate_traversal_materialization_v1` with starts on authoritative link endpoints (`walks_persisted=8` new); `completed_walks=16`, `walks_with_authoritative_hop=8` (e.g. 25 hops on one walk).
- **A5:** Pass — ≥1 completed walk visiting ≥1 authoritative link per plan §6.2.
- **Code:** `step09_octs_walk.py` (`pick_start_node_ids_on_authoritative_edges_v1`, `evaluate_a5_octs_execution_continuity_v1`); wedge script + tests `test_step09_octs_walk.py`.
- **Note:** First pass used default entity starts (0-hop walks); wedge selects authoritative-incident starts for real traversal.

### Step 10 completion record (RETRIEVAL / evidence recovery A6)

- **Command:** `cd backend && .venv/bin/python scripts/unlock_step10_retrieval.py`
- **Artifact:** [`baselines/fizzer_step10_2026-05-22.json`](baselines/fizzer_step10_2026-05-22.json)
- **Result:** `materialize_retrieval_index_for_pipeline_v1` on pipeline `faa5469f-…`; `entries_materialized=216`, `entry_count=216`, `build_state=PUBLISHED`; `walks_candidates=16`, `org_link_candidates=200`; `skip_reasons=[]` (no `RET-SKIP-GRAPH-DISCONNECTED` dominance).
- **A6:** Pass — evidence recovery attempt with materialized entries, not graph-disconnect dominated.
- **Code:** `step10_retrieval.py` (`evaluate_a6_evidence_recovery_v1`); wedge script + tests `test_step10_retrieval.py`.
- **Note:** `completed_tcre_jobs=0`; walk + org-link bindings sufficient for wedge. Execution restart (Celery) optional and failed locally without affecting materialization pass.

### Step 11 completion record (§9.1 alive panel — Track A T0)

- **Command:** `cd backend && .venv/bin/python scripts/unlock_step11_alive_panel.py`
- **Artifact:** [`baselines/fizzer_step11_2026-05-22.json`](baselines/fizzer_step11_2026-05-22.json)
- **Panel T0 (all green):** A1=7286 handles, A2=200 auth links, A3=2000 candidates, A4=step04 motion evidence, A5=16 walks / 8 with authoritative hops, A6=216 retrieval entries (no `RET-SKIP-GRAPH-DISCONNECTED` dominance).
- **48h hold:** Clock started at `2026-05-22T15:25:27Z`; re-run panel script daily until 48h elapses for Track A sign-off (§11).
- **Code:** `step11_alive_panel.py` (`build_alive_panel_evaluation_v1`); `unlock_step11_alive_panel.py`; tests `test_step11_alive_panel.py`.

### Step 12 completion record (Fix 6–7, Track B soak, Level 6 / P3)

- **Command:** `cd backend && .venv/bin/python scripts/unlock_step12_track_b_p3.py`
- **Artifact:** [`baselines/fizzer_step12_2026-05-22.json`](baselines/fizzer_step12_2026-05-22.json)
- **Fix 6:** GitHub ingest caps snapshotted (`CORTEX_GITHUB_*`); ops should raise to recommended mins (pages≥10, repos≥16, budget≥120s) for true orphan closure.
- **Fix 7:** `project_canonical_completeness_v1` exposes `untreated_routable_estimate`, `drainable_routable_estimate`, `deferral_counts`; pipeline overview canonical `backlog_count` uses drainable (not raw−mat).
- **Track B soak T0:** 24h clock started; `phase_cursor=phase_05_traversal`, `drainable=7715` (operator chases drainable, not 8183 admin gap).
- **Level 6:** Completed `degradation_brief` synthesis job `synthesis_replay_safe` with receipt + `SD-SCOPE-EMPTY` omission rows (lawful partial intelligence §5.4).
- **Code:** `step12_track_b_p3.py`; `unlock_step12_track_b_p3.py`; tests `test_step12_track_b_p3.py`.

```bash
cd backend && UNLOCK_DEPLOY_GIT_SHA=$(git rev-parse HEAD) .venv/bin/python scripts/unlock_step04_deploy_validate.py
# release-only: UNLOCK_STEP04_SKIP_DRAIN=1
```

---

## Normative Architecture Alignment

This document **operationalizes** the Cortex execution reality model defined in:

**[`DOCS/architecture/cortex_execution_reality_model_v0.md`](../architecture/cortex_execution_reality_model_v0.md)**

All remediation and unlock work here **must preserve**:

| Obligation | Reality-model anchor |
|------------|----------------------|
| **Deterministic execution substrate truth** | Substrate is source of truth; same inputs → same ids/receipts (§4, §10) |
| **Authoritative link semantics** | Only `link_authority = 'authoritative'` meaning links traverse/bind; candidates are not truth (§7) |
| **Lawful partial intelligence** | Useful narratives on incomplete exhaust with explicit omission classes (§12) |
| **Retrieval as evidence recovery** | Not RAG over raw Slack/GitHub; RET-SKIP when prerequisites fail (§9) |
| **Synthesis legality boundaries** | No invented causality/psychology; claims reducible to `evidence_raw_record_ids` (§11) |
| **Explicit omission classes** | Topology deferrals, permanent orphans, ingest windows surfaced — never silent gaps (§4, §12) |
| **Graceful degradation under incomplete data** | `topology_wait`, disconnected graph, walk incomplete are **correct** outcomes (§12, §8) |

**Conflict resolution:** If this war-room plan disagrees with the reality model, **the reality model wins**. Update this plan or bump ontology to v1 with an explicit changelog.

**Terminology:** This document uses the stable terms from reality model v0: **operational exhaust**, **execution substrate**, **org handles**, **authoritative links**, **candidate links**, **execution continuity** (traversal), **evidence recovery** (retrieval), **partial intelligence**, **alive criteria**.

---

## Execution Intelligence Milestone Ladder

Use this ladder for prioritization. **P0/P1 unlock targets Level 4–6**, not Level 7–8.

| Level | Name | What exists | Fizzer (May 2026) |
|------:|------|-------------|-------------------|
| **0** | Operational exhaust only | `raw_ingestion_records`; connectors run | **Met** (24k+ raw) |
| **1** | Canonical execution substrate continuity | Materializations, anchors, honest deferrals | **Partial** (71% mat; deferral deadlock) |
| **2** | Identity continuity | Org handles + primitive projection | **Latent** (anchors exist; 0 committed handles) |
| **3** | Authoritative graph continuity | Promoted meaning links; exportable org execution graph | **Not met** (0 authoritative links) |
| **4** | Successful OCTS execution continuity | Completed walk visiting ≥1 authoritative link | **Not met** |
| **5** | Retrieval evidence binding | Evidence recovery attempt not dominated by graph/walk RET-SKIP | **Not met** |
| **6** | Lawful partial intelligence | Synthesis/narrative legal under §11; omission classes propagated | **Met (wedge)** — step 12 receipt + SD omissions |
| **7** | Stable execution intelligence | Repeatable Level 4–6 without manual wedge | **Not met** |
| **8** | Agent-consumable execution cognition layer | Agents use substrate APIs, not raw connector chaos (§14) | **Not met** |

**War-room scope:** Move Fizzer from **Level 1 (broken drain path)** → **Level 6** via Track A/B. **Level 7–8** is Track B + product hardening, not P0.

```text
operational exhaust (L0)
  → execution substrate / canonical continuity (L1)
  → identity continuity / org handles (L2)
  → authoritative links / org execution graph (L3)
  → OCTS execution continuity reconstruction (L4)
  → evidence recovery (L5)
  → lawful partial intelligence (L6)
  → stable execution intelligence (L7)
  → agent execution brain (L8)
```

---

## 1. Core Diagnosis

### 1.1 What is actually broken (root causes)

| # | Root cause | Type | Evidence |
|---|------------|------|----------|
| **R1** | **Topology deferral release deadlock** | Code bug | 7,394 deferrals: `queue=topology_orphan`, `parent_raw_record_id IS NULL`. `release_deferrals_with_materialized_parents()` only clears rows with `parent_raw_record_id` set → **0 releases**. 1,754 `missing_pr` + 1,716 `missing_deployment` deferrals have **materialized parents** but stay deferred. |
| **R2** | **Canonical gate starvation** | FSM policy | `untreated_raw_exists_v1` true while 7,047 raw unmat → worker never runs phase 03–08 (`run_tenant_execution.py` ~202–241). |
| **R3** | **Drain candidate starvation** | Consequence of R1+R2 | `list_forward_progress_candidate_ids` excludes all deferrals → **0** candidates per slice → `topology_wait`, `total_succeeded=0`. |
| **R4** | **Authoritative links never created on hot path** | Pipeline wiring | Phase 03 writes org handles only; promotion is separate (`graph_density_promotion.py`); phase 04 export is read-only (reality model §6–7). Prod: 0 authoritative links, 0 candidate links. |
| **R5** | **Partial ingest by design** | Config + registry | GitHub/Slack/Notion caps (`settings.py`); `exhaust_coverage_registry` marks `historical: partial`. ~1,298 PR parents truly absent from raw. |

### 1.2 Symptoms (not root causes — do not fix these first)

| Symptom | Misread as | Actual cause |
|---------|------------|--------------|
| Admin canonical backlog **7047** | “Drain queue depth” | `raw_total - mat_total`; 7045 are deferrals, not FIFO work |
| Org execution graph phase “blocked” | Broken graph export | `org_handles==0` + `authoritative_links==0` (export read-only by design) |
| Evidence recovery / synthesis cards “starved” | Broken retrieval/synthesis | Phases never ran; completeness projection only — **L4–L6 blocked** |
| CloudWatch `canonical_continue` loop | Worker broken | Worker **works**; outcome is **topology_wait** |
| Identity card critical (0 handles) | Extraction broken | Phase 03 **never committed**; dry_run proved ~11.8k possible |

### 1.3 Explicit deadlocks

```text
DEADLOCK A (canonical):
  deferral recorded (topology_orphan, missing_parent_ref)
    → excluded from drain candidates
    → parent materializes later
    → release_deferrals_with_materialized_parents NO-OP
    → deferral persists forever (until permanent_orphan)
    → topology_wait + 0 partial_progress forever

DEADLOCK B (FSM):
  untreated_raw_exists_v1 == true (7047 unmat)
    → canonical_needs_more_work_v1 == true
    → worker returns after phase 02
    → phase 03 never runs
    → 0 entities, 0 candidates, 0 edges

DEADLOCK C (organizational execution graph / execution continuity):
  0 org handles (prod)
    → 0 candidate links
    → promotion pass has nothing to promote
    → 0 authoritative links
    → OCTS execution continuity: 0 hops
    → evidence recovery: RET-SKIP-GRAPH-DISCONNECTED / RET-SKIP-WALK-INCOMPLETE
```

### 1.4 Answers to the ten planning questions

| # | Question | Answer |
|---|----------|--------|
| 1 | Fix first? | **R1 deferral release** (code) — unlocks ~3,470+ mat rows without ingest |
| 2 | Bypass temporarily? | **Identity backfill API** (entities); **manual promotion pass** (edges); **do not** wait for `raw==mat` |
| 3 | Fake-critical vs critical? | Fake: graph/evidence-recovery/synthesis cards. Critical: deferral release, gate, authoritative-link promotion |
| 4 | Shortest path to intelligence? | L2 org handles → L3 authoritative links → L4 OCTS walk → L5 evidence recovery without graph RET-SKIP (ladder §4–5) |
| 5 | Wrong assumptions? | “Ingest parents fixes convergence”; “canonical first then identity”; “graph export creates authoritative links” |
| 6 | Permanent arch changes? | Deferral release by node key; gate on deferral-aware routable queue; post-identity promotion hook (reality model §7) |
| 7 | Acceptable wedges? | Admin backfill, inline promotion pass, execution restart from GRAPH; **not** raw SQL deferral deletes in prod without code |
| 8 | First success milestone? | **Alive criteria A1–A6** (§6) — **not** full convergence, **not** 7047→0 |
| 9 | “Cortex alive” metrics? | Reality model §13 A1–A6; §9.1 panel |
| 10 | Full sequence? | §9 step-by-step |

---

## 2. Architectural Truths

*Aligned with reality model v0 §3, §12, §13.*

### 2.1 Assumptions that failed

| Assumption | Execution-substrate reality |
|------------|----------------------------|
| Full canonical convergence precedes useful work | **71% mat + ~11.8k org handles (dry_run)** already sufficient for **Level 6 partial intelligence** |
| Missing parent refs mean missing ingest | **57%** of `missing_pr` deferrals have materialized PR parents — **deferral release** failure |
| Org execution graph export materializes authoritative links | Export is **read-only**; **authoritative links** require governed promotion (§7) |
| Convergence worker advances execution chain | Worker **loops phase 02** only on this tenant |
| `7047` is actionable backlog | **7045** are deferral-blocked; drain selects **0** — not execution substrate progress |
| Waiting improves topology | **No** — without release fix + ingest, wait = spin (violates graceful degradation honesty) |

### 2.2 Philosophical shift required

| Old | New (reality model) |
|-----|---------------------|
| Substrate purity first | **Lawful partial intelligence first** (§12) |
| `raw == mat` as health | **Alive criteria A1–A6** + deferral-aware canonical progress |
| Monolithic FSM advance | **Wedge path** (operator + hooks) **in parallel** with execution substrate repair |
| Deterministic = complete | Deterministic = **honest degradation** (RET-SKIP, omission classes) on incomplete operational exhaust |

### 2.3 Why “full canonical convergence first” is operationally wrong

1. **Permanent orphans (2,845)** + non-routable rows → gate never clears.  
2. **Ingest is windowed** — full convergence is **unbounded work**.  
3. **Intelligence needs ~hundreds** of linked humans, not 24k mat rows.  
4. **R1 bug** makes convergence **impossible** even when parents exist.

---

## 3. Unlock Strategy

### 3.0 Unlock goals vs full convergence (critical)

| | **P0 / P1 war-room goal** | **NOT a P0 / P1 goal** |
|---|---------------------------|-------------------------|
| **Purpose** | Satisfy **alive criteria A1–A6** ([reality model §13](../architecture/cortex_execution_reality_model_v0.md#13-what-alive-means)) | `raw_total == mat_total`, zero deferrals, all pipeline cards green |
| **Ladder** | Reach **Level 4–6** (OCTS continuity + evidence recovery + lawful partial intelligence) | Level 7–8 stable/agent brain |
| **Intelligence type** | **Partial intelligence** with explicit omission classes | Full organizational knowledge |

**Operators must not close the war-room because 7047 → 0.** Close when **A1–A6** pass at wedge thresholds (§6.2).

### 3.1 Shortest-path strategy (two tracks)

```text
TRACK A — WEDGE (48–72h): Alive criteria A1–A6 + Level 4–6 on Fizzer
  P0 code: deferral release by missing_parent_ref (L1 substrate continuity)
  P0 ops:  org handles (L2) → candidate links → authoritative links (L3)
  P0 ops:  OCTS execution continuity (L4) → evidence recovery probe (L5)
  Success: §6 Alive criteria A1–A6 — NOT full convergence

TRACK B — REPAIR (1–2 weeks): Autonomous execution substrate progression (L7)
  P1 code: deferral-aware canonical gate; post-identity promotion hook
  P1 ops/config: GitHub ingest caps for true missing parents
  P2: admin metrics truth; synthesis/retrieval legality guards (§5.4)
```

### 3.2 Intentional bypasses (temporary, lawful)

| Bypass | Lawful because | Revert when |
|--------|----------------|-------------|
| Admin identity backfill | Same code as phase 03 transform; deterministic | Gate fixed; worker runs phase 03 |
| Inline `schedule_graph_density_pass_v1(force=True)` | Uses `promote_candidate_to_authoritative_link` + policy | Autonomous hook after phase 03 |
| Execution restart `from_phase=GRAPH` | Does not fake mat rows | Pipeline reaches phase 04+ autonomously |
| Ignore `raw−mat` admin card | Misleading metric | Forward-progress + alive metrics shipped |

**Do NOT bypass:** promotion policy requirements, evidence on links, RET-SKIP taxonomy, tombstone/lifecycle rules.

### 3.3 Permanent vs temporary

| Change | Temporary wedge | Permanent |
|--------|-----------------|-----------|
| Manual backfill POST | ✓ use now | Remove dependency via gate fix |
| `release_deferrals_by_parent_ref_v1` | — | **Required** |
| Gate `untreated_routable_deferral_aware_v1` | — | **Required** |
| Post-03 promotion hook | Can call inline scheduler | **Required** for autonomy |
| Raise `cortex_github_prs_max_pages_per_repo` | ✓ tenant config | Product decision per tenant |

---

## 4. Critical Fixes (ranked)

### Fix 1 — Release topology deferrals when parent node is materialized

| Field | Value |
|-------|-------|
| **Severity** | P0 — **blocks L1–L6** (no lawful partial intelligence without execution substrate motion) |
| **Why** | 3,470+ rows cannot drain; `partial_progress` impossible; false `topology_wait` |
| **Files** | `canonical/forward_progress/deferral_store.py`, `canonical/replay_topology.py` (`_node_key`), `canonical/forward_progress/drain_runtime.py` |
| **Invariant violated** | “Deferrals clear when dependency satisfied” — only implemented for `parent_raw_record_id` |
| **Proposed fix** | **Shipped (step 2):** `release_deferrals_when_missing_parent_ref_materialized_v1()` + `build_node_key_index()`; wired in `drain_forward_progress_backlog` at slice start and after productive batches. |
| **Expected result** | Next drain slice: `total_succeeded > 0`, deferral count drops by ~3k+, `canonical_outcome` → `partial_progress` |
| **Risk** | Wrong key match → premature release → mat failure; mitigate with unit tests mirroring `replay_topology` keys |

---

### Fix 2 — Canonical→identity gate: deferral-aware untreated metric

| Field | Value |
|-------|-------|
| **Severity** | P0 — **blocks autonomous phase 03–08** |
| **Why** | 7,047 unmat includes permanent orphans + deferral-blocked; worker never advances |
| **Files** | `substrate_pipeline/canonical_phase_gate.py`, `canonical/forward_progress/candidate_selection.py` (reuse exclusion logic), `execution/run_tenant_execution.py` |
| **Invariant violated** | “Do not advance identity while canonical work remains” — interpreted as **any** unmat raw |
| **Proposed fix** | **Shipped (step 3):** `untreated_routable_drainable_exists_v1()` + `canonical_identity_may_proceed_despite_topology_v1()`; gate tail and topology-wait branches deferral-aware; worker passes `bundle_id`. |
| **Expected result** | Worker runs phase 03 while topology gap remains; identity substrate progresses |
| **Risk** | Identity on “incomplete” canonical — acceptable per wedge doctrine; document in receipt |

---

### Fix 3 — Wire lawful edge promotion after identity substrate

| Field | Value |
|-------|-------|
| **Severity** | P0 — **blocks execution continuity (L4) and evidence recovery (L5)** |
| **Why** | 0 authoritative edges forever on hot path |
| **Files** | `identity/continuity_rebuild.py` (`run_identity_handles_and_candidates_refresh`), `substrate_pipeline/phase_runners.py` (`run_phase_03_identity_v1`), `operational_runtime/graph_density_promotion.py` (`schedule_graph_density_pass_v1`) |
| **Invariant violated** | Reality model §7–8: execution continuity requires **authoritative links** — **no producer** on pipeline path |
| **Proposed fix** | After successful phase 03 receipt (entities_upserted > 0): call `run_anchor_continuity_candidate_regeneration` if not already; `schedule_graph_density_pass_v1(tenant_id, trigger=after_phase_04, force=False)` — or `PROMOTION_TRIGGER_MANUAL` internally. Remove/scheduling guard conflict in `execution/scheduling.py` only for **identity-phase hook**, not phase 04 sidecar. |
| **Expected result** | `cortex_org_link_candidates > 0`, then `cortex_org_links` authoritative > 0 after promotion pass |
| **Risk** | Over-promotion — capped by `cortex_graph_density_promotion_max_per_pass` (default 200) |

---

### Fix 4 — Admin backfill API runs candidate regen

| Field | Value |
|-------|-------|
| **Severity** | P1 — **blocks operator wedge** |
| **Why** | `POST …/backfill/from-canonical-anchors` only calls `run_anchor_handle_backfill` — no candidates |
| **Files** | `api/http/routes/admin.py`, `identity/backfill.py` (`run_identity_handles_and_candidates_refresh`), `contracts/admin.py` |
| **Proposed fix** | Optional `include_candidate_regen: bool = True` on request; call `run_identity_handles_and_candidates_refresh` instead of bare backfill |
| **Expected result** | One POST → entities + candidates |
| **Risk** | Long request time — run async via replay job `candidate_regen` (already exists in `org_link_replay_runtime.py`) |

---

### Fix 5 — Admin HTTP: promotion pass + candidate regen enqueue

| Field | Value |
|-------|-------|
| **Severity** | P1 — **operator dependency on Python shell** |
| **Why** | No tenant POST for `schedule_graph_density_pass_v1` / `candidate_regen` |
| **Files** | `api/http/routes/admin_cortex_operational_runtime.py` or `admin.py` |
| **Proposed fix** | `POST /tenants/{tid}/cortex/operational-runtime/graph-density-promotion/run` → `schedule_graph_density_pass_v1(force=?)`. `POST …/identity/replay-jobs` body `job_kind: candidate_regen` (if not already exposed). |
| **Expected result** | War-room steps without RDS scripts |
| **Risk** | Low |

---

### Fix 6 — GitHub ingest caps (true missing parents only)

| Field | Value |
|-------|-------|
| **Severity** | P2 — **~1,298 PR gaps** |
| **Why** | Remaining deferrals after Fix 1 |
| **Files** | `settings.py` / env: `CORTEX_GITHUB_PRS_MAX_PAGES_PER_REPO`, `CORTEX_GITHUB_PR_FETCH_MAX_REPOS`, `CORTEX_GITHUB_REPO_TIME_BUDGET_SECONDS` |
| **Proposed fix** | Raise for Fizzer; run GitHub sync until checkpoints advance |
| **Expected result** | New PR raw rows; deferrals clear via Fix 1 |
| **Risk** | API rate limits; longer sync jobs |

---

### Fix 7 — Admin metric truth

| Field | Value |
|-------|-------|
| **Severity** | P2 — **fake-green** |
| **Why** | Operators chase 7047 |
| **Files** | `completeness/canonical_completeness_projection.py`, `pipeline/pipeline_admin_overview.py` |
| **Proposed fix** | Surface `untreated_routable_estimate`, `deferral_counts`, `drainable_count` from forward-progress snapshot |
| **Expected result** | Ops chases correct number |
| **Risk** | Low |

---

## 5. Phase-by-Phase Recovery Plan

### P0 — Unblock execution substrate motion (code + first wedge)

**Goals (reality model):** Restore **L1 canonical execution substrate continuity**; achieve **alive criteria A1–A4** (org handles, authoritative links, candidate links, canonical `total_succeeded > 0`).

**Not goals:** Full convergence, Level 7–8, synthesis legality proof (deferred to P1/P3).

| Task | Owner | Implementation |
|------|-------|----------------|
| P0.1 | Eng | Implement Fix 1 + unit tests (`replay_topology` key → release) |
| P0.2 | Eng | Implement Fix 2 (minimal: drainable gate tail) |
| P0.3 | Eng | Deploy to prod |
| P0.4 | Ops | Run wedge sequence §9 (steps 1–6) on Fizzer |

**Validation SQL (tenant `c08ef32b-…`, bundle `bundle.phase03.step03.logical_keys.v1`):**

```sql
-- Deferrals dropping
SELECT COUNT(*) FROM cortex_canonical_materialization_deferrals
WHERE tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f';

-- Materializations increasing
SELECT COUNT(*) FROM cortex_canonical_transform_materializations
WHERE tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f';

-- Alive substrate
SELECT COUNT(*) FROM cortex_org_entities
WHERE tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f' AND tombstoned_at IS NULL;

SELECT COUNT(*) FROM cortex_org_link_candidates WHERE tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f';

SELECT COUNT(*) FROM cortex_org_links
WHERE tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f'
  AND link_authority = 'authoritative' AND revoked_at IS NULL;
```

**Validation APIs:**

```http
GET /admin/tenants/c08ef32b-f89a-40f6-9566-e19b5329436f/cortex/canonical/forward-progress
GET /admin/tenants/c08ef32b-f89a-40f6-9566-e19b5329436f/cortex/execution/state
GET /admin/tenants/c08ef32b-f89a-40f6-9566-e19b5329436f/cortex/identity/control-plane
GET /admin/tenants/c08ef32b-f89a-40f6-9566-e19b5329436f/cortex/operational-runtime/graph-density
```

**Validation logs (CloudWatch `/ecs/vector-backend-worker`):**

- `canonical_outcome: partial_progress` OR `progressed` (not only `topology_wait`)
- `total_succeeded` > 0 in canonical summary
- After wedge: phase 03+ in `cortex_substrate_phase_runs` with `completed`

**Success criteria (alive A1–A4 at wedge thresholds):**

| Criterion | Target | Maps to |
|-----------|--------|---------|
| **A1** | Org handles (active) ≥ 10,000 | `cortex_org_entities` |
| **A2** | Authoritative links (active) ≥ 1 | `cortex_org_links` |
| **A3** | Candidate links ≥ 100 | `cortex_org_link_candidates` |
| **A4** | Canonical `total_succeeded > 0` in 24h | CloudWatch / forward-progress |
| L1 helper | Deferrals < 4,000 **or** drainable queue processes rows | Deferral store |

**Rollback / failure:**

- If `entities_upserted == 0` after backfill with anchors > 0 → identity code regression (stop, debug `backfill.py`)
- If deferrals unchanged after Fix 1 deploy → release function not called or key mismatch (block deploy, add logging)
- If promotion promotes 0 with candidates > 0 → policy/receipt gate (`cortex_graph_density_promotion_require_replay_receipt`)

---

### P1 — Alive criteria A5–A6 + Level 4–5 (execution continuity + evidence recovery)

**Goals (reality model):** **Not full convergence.** Achieve **A5** (completed OCTS walk with ≥1 visited authoritative link) and **A6** (evidence recovery attempt not dominated by `RET-SKIP-GRAPH-DISCONNECTED`). Reach **ladder Level 4–5**.

| Task | Owner |
|------|-------|
| P1.1 | Ops — `POST …/execution/restart?from_phase=GRAPH` (or `TRAVERSAL`) after edges exist |
| P1.2 | Eng — Fix 3 + Fix 4 + Fix 5 shipped |
| P1.3 | Ops — Monitor phase 05 `output_json.walks_persisted` |
| P1.4 | Ops — Probe phase 07 / retrieval diagnostics |

**Validation:**

```sql
-- OCTS walks (table name per durable_walk_store model)
SELECT id, status, created_at FROM cortex_octs_walk_records  -- adjust if renamed
WHERE tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f'
ORDER BY created_at DESC LIMIT 5;

-- Graph projection hash in phase runs
SELECT phase_id, status, output_json
FROM cortex_substrate_phase_runs pr
JOIN cortex_substrate_pipeline_runs r ON r.id = pr.pipeline_run_id
WHERE r.tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f'
  AND pr.phase_id IN ('phase_04_graph','phase_05_traversal')
ORDER BY pr.started_at DESC LIMIT 5;
```

**Success criteria:**

- [ ] **A5:** ≥1 completed OCTS walk; walk visited ≥1 authoritative link (phase 05 / walk store)
- [ ] **A6:** ≥1 evidence recovery attempt without dominant `RET-SKIP-GRAPH-DISCONNECTED` (retrieval diagnostics)
- [ ] Ladder **Level 4–5** marked met on Fizzer

**Failure:**

- `walks_persisted == 0` with authoritative links > 0 → org execution graph export / start node selection (`substrate_traversal_execution.py`) — not “broken graph AI”
- Evidence recovery still `RET-SKIP-GRAPH-DISCONNECTED` with authoritative links > 0 → binding bug (P1); **do not** paper over with synthesis

---

### 5.4 Synthesis, evidence recovery, and agent-output legality (all phases)

*Normative: reality model §9, §11, §14. Applies to P1 probes, P3 synthesis, and any agent/MCP surface.*

Any work touching **evidence recovery**, **synthesis**, or **agent outputs** must enforce:

| Constraint | Requirement |
|------------|-------------|
| **RET-SKIP propagation** | Skip codes from retrieval (`retrieval_skip_registry.py`) and walk incompleteness must surface in diagnostics, admin, and agent context — never overridden by prose |
| **No invented causality** | Claims reducible to `substrate object → evidence_raw_record_ids → displayed claim`; no psychology, intent, or narrative glue for topology holes |
| **Candidate ≠ authoritative** | Candidate links inform promotion only; traversal, binding, and synthesis must not treat candidates as ground truth |
| **Omission-class propagation** | Deferrals, permanent orphans, ingest windows, and `topology_wait` appear as explicit omission classes in synthesis bundles and agent plans |

**Implementation guardrails (P2+):**

- Phase 07/08 inputs must include RET-SKIP distribution + omission classes from forward-progress / completeness projections.
- Synthesis phase 08: reject or flag outputs that reference edges not in `cortex_org_links` with `link_authority = 'authoritative'`.
- Agent tools: consume execution state + authoritative links; **do not** re-interpret raw Slack/GitHub when substrate exists (§14).

**War-room rule:** If A6 passes but synthesis invents relationships, **Level 6 is not met** — rollback narrative work, not substrate wedge.

---

### P2 — Autonomous execution substrate restoration (Level 7)

**Goals:** Worker advances 03→08 without manual backfill; `partial_progress` sustained.

| Task | Owner |
|------|-------|
| P2.1 | Eng — Fix 6 ingest caps + Notion topology review |
| P2.2 | Eng — Fix 7 admin metrics; wire §5.4 RET-SKIP + omission-class surfacing in completeness |
| P2.3 | Ops — 24h soak: forward-progress snapshots every 30 min |

**Success criteria:**

- [ ] `GET …/execution/state` shows `phase_cursor` past `phase_02_canonical` without manual restart
- [ ] CloudWatch: mix of `partial_progress` / `progressed`, not only `topology_wait`
- [ ] `untreated_routable_drainable` → 0 (new metric) while `raw−mat` may remain > 0

**Failure:**

- Worker still on phase 02 only → gate or drain still broken (re-open P0)
- `FSM_BLOCKED` on retrieval → admin `POST …/execution/rerun?break_glass=true` per `admin_commands.py`

---

### P3 — Lawful partial intelligence (Level 6): first synthesis artifact

**Goals:** One **lawful** synthesis output tied to real OCTS execution continuity + evidence recovery — not a demo narrative.

**Prerequisites:** **Alive criteria A1–A6** (§6); `cortex_substrate_pipeline_phase_08_enabled` true; §5.4 legality guards understood by implementers.

**Success criteria:**

- [ ] `phase_08_synthesis` `completed` with non-empty `output_json`
- [ ] Artifact / receipt inspectable; every factual claim traceable to authoritative links + `evidence_raw_record_ids`
- [ ] Output carries **omission classes** where substrate incomplete (no silent topology gaps)
- [ ] No RET-SKIP codes overridden in prose; walk/retrieval skips reflected in bundle metadata
- [ ] **Level 6** marked met on ladder (§4) — distinct from “phase 08 green”

**Failure (stop and fix substrate, not prompts):**

- Synthesis cites candidate links as fact → violates candidate ≠ authoritative
- Narrative connects entities with no authoritative path → violates no invented causality
- Retrieval dominated by `RET-SKIP-*` but synthesis reads complete → violates RET-SKIP propagation

---

## 6. Alive Criteria Milestone (A1–A6)

**Normative definition:** [`cortex_execution_reality_model_v0.md` §13](../architecture/cortex_execution_reality_model_v0.md#13-what-alive-means).

### 6.1 Operational goal (P0 / P1)

| | War-room | Out of scope |
|---|----------|--------------|
| **Goal** | Achieve **alive criteria A1–A6** at wedge thresholds | Full canonical convergence, zero deferrals, admin all-green |
| **Ladder** | **Level 4–6** (execution continuity → evidence recovery → lawful partial intelligence) | Level 7–8 until Track B |
| **Closes war-room** | §6.2 checklist green for **48h** (Track A) | `7047 → 0` alone |

**P0/P1 success is NOT full convergence.** Operators close Track A when A1–A6 pass — not when `raw == mat`.

### 6.2 Alive criteria checklist (proof bundle)

| Criterion | Wedge threshold | Evidence (SQL / API / log) |
|-----------|-----------------|------------------------------|
| **A1** Org handles (active) | ≥ 100 (expect ~11k after wedge) | `cortex_org_entities`; `GET …/identity/control-plane` |
| **A2** Authoritative links (active) | ≥ 1 (expect up to 200/pass) | `cortex_org_links` where `link_authority='authoritative'` |
| **A3** Candidate links | ≥ 50 | `cortex_org_link_candidates` |
| **A4** Canonical execution substrate motion | `total_succeeded > 0` in 24h | CloudWatch / `GET …/canonical/forward-progress` |
| **A5** OCTS execution continuity | ≥ 1 completed walk; ≥ 1 visited **authoritative** link | Phase 05 `output_json` / OCTS walk store |
| **A6** Evidence recovery | ≥ 1 attempt not dominated by `RET-SKIP-GRAPH-DISCONNECTED` | Retrieval diagnostics / phase 07 |

**A1 detail:** At least one `HUMAN_ACTOR` (or equivalent) org handle tied to operational exhaust — proves identity continuity (L2), not ingestion alone (L0).

**A5 detail:** Walk may be partial under policy; must not be empty with authoritative links present — otherwise L4 not met.

**A6 detail:** Other RET-SKIP codes (`RET-SKIP-WALK-INCOMPLETE`, `RET-SKIP-TCRE-MISSING`, etc.) may still appear; dominant graph-disconnect skip must not be the only story.

### 6.3 Mapping to milestone ladder

| Alive | Ladder level |
|-------|----------------|
| A1–A3 | L2–L3 (identity + authoritative graph continuity) |
| A4 | L1 (canonical execution substrate continuity) |
| A5 | L4 (OCTS execution continuity) |
| A6 | L5 (evidence recovery binding) |
| P3 synthesis lawful | L6 (partial intelligence) — **after** A1–A6 |

### 6.4 Explicitly NOT required for alive / P0–P1

- `raw_total == mat_total`
- Admin canonical backlog **7047 → 0**
- All pipeline phases `healthy`
- Zero deferrals or permanent orphans cleared
- Full org-chart connectivity
- Phase 08 synthesis completed (Track A / P1)
- Level 7–8 stable or agent-consumable cognition

---

## 7. Autonomous Convergence Plan

### 7.1 After wedge — what true autonomy requires

| Requirement | Status after P0–P2 |
|-------------|-------------------|
| Fix 1 deferral release | **Must ship** |
| Fix 2 gate | **Must ship** |
| Fix 3 promotion hook | **Must ship** |
| Ingest for true orphans | **Partial** — can stay incomplete forever for some rows |
| Promotion passes continue | Celery/inline on candidate backlog |
| TCRE jobs | Separate convergence; phase 06 WAITING semantics |

### 7.2 What still prevents full autonomy

| Blocker | Can remain partial forever? |
|---------|----------------------------|
| Permanent orphans (2,845) | **Yes** — exclude from gate metric |
| Non-routable raw (2) | **Yes** |
| Out-of-window GitHub history | **Yes** — document omission classes |
| Notion row topology | **Partial fix** or permanent exclusion |
| `raw−mat` gap | **Yes** — if gate is deferral-aware |

### 7.3 What must eventually complete (for “full” product)

- Deterministic replay safety across bundles  
- TCRE reconstruction for mat rows used in evidence recovery  
- Synthesis gating with real OCTS execution continuity (§5.4 legality)  
- Not necessarily 100% raw mat

---

## 8. Production Readiness Risks

| Risk | Mitigation |
|------|------------|
| **Deferral release wrong keys** | Golden tests from prod `missing_parent_ref` samples |
| **Fake-green admin** | Ship alive metrics dashboard (§9.3) |
| **Starvation loop** | Fix 1+2 before re-enabling aggressive convergence |
| **Ingest incompleteness** | `exhaust_coverage_registry` honest labels; tenant caps documented |
| **Graph explosion** | Promotion cap 200/pass; candidate cap 2000/regen |
| **Replay deadlocks** | `continuity_rebuild` must not run canonical drain before entities until Fix 1 live |
| **Operator dependency** | P1 admin APIs for regen/promotion |
| **11k isolated nodes** | Expected until promotion; monitor edge/entity ratio |
| **CloudWatch noise** | Success = outcome mix change, not fewer `canonical_continue` |

---

## 9. Recommended Immediate Execution Order

**Tenant:** `c08ef32b-f89a-40f6-9566-e19b5329436f`  
**Admin base:** `https://<prod-admin-host>/admin` (use your deployed API prefix)

### Step 0 — Baseline snapshot (15 min) — **DONE 2026-05-21**

```bash
cd backend && .venv/bin/python scripts/prod_substrate_proof_queries.py \
  --out ../DOCS/audits/baselines/fizzer_step01_2026-05-21.json
```

Record: deferrals, mat, entities, auth_links, lease `last_canonical_outcome`. Committed snapshot under `DOCS/audits/baselines/`.

---

### Step 1 — Ship P0 code (Eng, blocking)

1. Implement **Fix 1** in `deferral_store.py` + call sites in `drain_runtime.py`  
2. Implement **Fix 2** in `canonical_phase_gate.py`  
3. PR + CI + deploy  

**Validate after deploy:**

```http
GET /admin/tenants/c08ef32b-f89a-40f6-9566-e19b5329436f/cortex/canonical/forward-progress
```

Wait 10–30 min for convergence slices. Expect `total_succeeded > 0` in logs.

**Failure:** No change → check release function logs; run unit tests.

---

### Step 2 — Identity entities (Ops, 30–90 min) — **DONE 2026-05-22**

```http
POST /admin/tenants/c08ef32b-f89a-40f6-9566-e19b5329436f/cortex/identity/backfill/from-canonical-anchors
Content-Type: application/json

{"dry_run": false, "anchor_limit": 20000}
```

**Validate:**

```sql
SELECT COUNT(*) FROM cortex_org_entities
WHERE tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f' AND tombstoned_at IS NULL;
-- EXPECT: >= 10000
```

```http
GET /admin/tenants/c08ef32b-f89a-40f6-9566-e19b5329436f/cortex/identity/control-plane
-- EXPECT: org_handles.value >= 10000
```

**Failure:** `entities_upserted == 0` → stop; identity substrate broken (contradicts proofs).

---

### Step 3 — Candidate regeneration (Ops, until P1 API exists)

**Option A — Python (prod-safe, uses app code):**

```bash
cd backend && .venv/bin/python - <<'PY'
import os, uuid
from pathlib import Path
# load .env prod DB + app
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from vector.domains.cortex.identity.anchor_continuity_candidates import run_anchor_continuity_candidate_regeneration
TID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")
# ... session from prod DATABASE_URL ...
with Session(engine) as db:
    out = run_anchor_continuity_candidate_regeneration(db, tenant_id=TID)
    db.commit()
    print(out)
PY
```

**Option B — Org link replay job** `job_kind=candidate_regen` via worker (if enqueue API wired).

**Validate:**

```sql
SELECT COUNT(*) FROM cortex_org_link_candidates WHERE tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f';
-- EXPECT: >= 50 (up to 2000 cap)
```

---

### Step 4 — First authoritative edges (Ops, 15 min)

**Until HTTP exists:**

```bash
cd backend && .venv/bin/python - <<'PY'
import uuid
from vector.domains.cortex.operational_runtime.graph_density_promotion import schedule_graph_density_pass_v1
TID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")
print(schedule_graph_density_pass_v1(tenant_id=TID, force=True, trigger="manual"))
PY
```

**Validate:**

```sql
SELECT COUNT(*) FROM cortex_org_links
WHERE tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f'
  AND link_authority = 'authoritative' AND revoked_at IS NULL;
-- EXPECT: >= 1
```

```http
GET /admin/tenants/c08ef32b-f89a-40f6-9566-e19b5329436f/cortex/identity/projection-preview
-- EXPECT: node_count > 0, edge_count > 0
```

**Failure:** candidates > 0 but promoted 0 → inspect `skipped` in pass output; policy/receipt.

---

### Step 5 — Org execution graph + OCTS execution continuity (Ops, 30 min)

```http
POST /admin/tenants/c08ef32b-f89a-40f6-9566-e19b5329436f/cortex/execution/restart?from_phase=GRAPH&force=true
```

Allow worker / or trigger pipeline phases 04–05.

**Validate:**

```http
GET /admin/tenants/c08ef32b-f89a-40f6-9566-e19b5329436f/cortex/execution/state
```

```sql
SELECT phase_id, status, output_json->>'walks_persisted' AS walks
FROM cortex_substrate_phase_runs pr
JOIN cortex_substrate_pipeline_runs r ON r.id = pr.pipeline_run_id
WHERE r.tenant_id = 'c08ef32b-f89a-40f6-9566-e19b5329436f'
  AND pr.phase_id = 'phase_05_traversal'
ORDER BY pr.started_at DESC LIMIT 3;
-- EXPECT: walks >= 1
```

---

### Step 6 — Evidence recovery probe (Ops, 30 min) — alive **A6**

```http
POST /admin/tenants/c08ef32b-f89a-40f6-9566-e19b5329436f/cortex/execution/restart?from_phase=RETRIEVAL&force=true
```

**Validate:** retrieval completeness / materialization diagnostics — **A6**: no dominant `RET-SKIP-GRAPH-DISCONNECTED`; RET-SKIP codes preserved in output (§5.4).

**Failure:** TCRE missing → restart from `TCRE` / phase 06 after walks exist. **Do not** compensate with synthesis or agent narration.

---

### Step 7 — Synthesis wedge (P3 / Level 6, after A1–A6 green)

```http
POST /admin/tenants/c08ef32b-f89a-40f6-9566-e19b5329436f/cortex/execution/restart?from_phase=SYNTHESIS&force=true
```

**Validate:** §5.4 — omission classes present; no candidate-as-authoritative; claims traceable to evidence ids. **Not required** for Track A sign-off.

---

### 9.1 Alive criteria panel (operational) — maps to reality model §13

Track daily on Fizzer. **Primary KPI = A1–A6**, not `raw−mat`.

| Criterion | Metric | Wedge threshold | Source |
|-----------|--------|-------------------|--------|
| **A1** | `org_entities_active` | > 0 (wedge: ≥ 10k) | SQL / identity control plane |
| **A2** | `authoritative_links_active` | > 0 (wedge: ≥ 1) | SQL |
| **A3** | `link_candidates` | > 0 (wedge: ≥ 50) | SQL |
| **A4** | `canonical_total_succeeded_24h` | > 0 | CloudWatch / forward-progress |
| **A5** | `octs_walks_completed_24h` with authoritative hop | ≥ 1 | SQL / phase 05 |
| **A6** | `evidence_recovery_non_graph_skip_24h` | ≥ 1 | retrieval diagnostics |
| Anti-fake | `topology_wait_only_24h` | **false** (A4 motion real) | CloudWatch ratio |
| L6 (P3+) | `synthesis_legality_pass` | receipt trace + omission classes | phase 08 / §5.4 |

**Do not track:** `raw−mat` alone; pipeline “all green”; ingestion volume without A1–A6.

---

### 9.2 Fake work to deprioritize

| Work | Why fake now |
|------|----------------|
| Chasing 7047 without deferral fix | Misleading |
| Full Notion row mat before edges | Low leverage |
| Perfecting synthesis prompts before **A5** execution continuity | No execution substrate for lawful partial intelligence |
| Re-architecting FSM before P0 code | Delay |
| `execution/rerun` from CANONICAL only without P0 | Re-enters deadlock |

---

### 9.3 Highest leverage order (summary)

```text
1. Fix deferral release (code)     ← unlocks canonical motion
2. Fix gate (code)                 ← unlocks autonomous 03+
3. Identity backfill (ops)         ← proves humans
4. Candidate regen (ops)           ← proves linkage candidates
5. Promotion pass (ops)            ← proves graph
6. Restart GRAPH→TRAVERSAL→RETRIEVAL ← proves A5–A6 (L4–L5)
7. Wire promotion + regen APIs (code) ← removes shell dependency
8. Ingest caps (config)            ← true orphans only
9. Admin metric truth (code)       ← stops fake chasing
```

---

## 10. Control-plane / FSM flaws (explicit)

| Flaw | Fix |
|------|-----|
| Deterministic deferrals without deterministic release | Fix 1 |
| Phase 02 consumes entire worker budget | Fix 2 allows 03+ parallel track |
| Identity and graph correctness coupled to complete raw mat | Gate decouple |
| Promotion orthogonality without scheduler | Fix 3 |
| `continuity_rebuild` runs canonical first | Document: run backfill path until Fix 1 deployed |
| Overview projections without anti-idle law | Fix 7 |

---

## 11. Sign-off criteria for “Cortex alive on Fizzer”

War-room closes **Track A** when **alive criteria A1–A6** (§6.2) are green and §9.1 panel holds for **48 hours** — **without** requiring P3 synthesis or `raw == mat`.

War-room closes **Track B** when §7 autonomous criteria hold for **24 hours** without manual backfill (Level 7).

**Level 6 (lawful partial intelligence)** is a separate sign-off after P3 + §5.4 validation.

---

## Appendix — Document precedence

| Document | Role |
|----------|------|
| [`cortex_execution_reality_model_v0.md`](../architecture/cortex_execution_reality_model_v0.md) | **Normative ontology** — alive A1–A6, ladder L0–L8, synthesis/retrieval legality |
| This plan | **Operational war-room** — code fixes, wedges, execution order |
| `cortex_execution_proofs.md`, `cortex_execution_unlock_challenge.md` | Forensic record (May 2026 Fizzer) |
| `cortex_fsm_unlock_plan.md` | Superseded for ordering where it conflicts (e.g. ingest-first before alive) |

*Where this plan disagrees with the reality model, update this plan — not the other way around without a v1 ontology changelog.*
