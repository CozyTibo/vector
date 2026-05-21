# Cortex Admin Revamp Plan

**Status:** Wave 0 signed off · Wave 1 complete · Wave 2 complete · Wave 3 complete (2026-05-21)  
**Scope:** `/admin/tenants/:tenantId/cortex/*` only (not workspace, integrations, or global admin)  
**Authoritative execution model:** `DOCS/cortex/CORTEX_SIMPLIFICATION_AND_DETERMINISM_REFACTOR.md` (M8 done)  
**Substrate prerequisite:** `DOCS/cortex/CORTEX_TRUE_P0_SIGN_OFF.md` (signed off)  
**Last updated:** 2026-05-21

---

## 1. Problem statement

Today Cortex Admin is a **research console**: dozens of tabs, replay/rebuild/regenerate vocabulary, doctrine surfaces (legality, certification, closure, equivalence), and CTAs that **bypass or duplicate** the single tenant execution path.

Operators cannot answer in 15 seconds:

1. Where is the pipeline right now?
2. What is blocked, missing, or degraded?
3. What is the one safe action to take?

**Goal:** A **plane control panel** — linear, calm, deterministic. Show state + gaps + at most one action per screen. Everything else is Cursor/debug tooling, not operator UI.

---

## 2. Non-negotiable principles

| # | Principle |
|---|-----------|
| P1 | **One execution path** — Admin commands only the execution engine (`POST …/cortex/execution/*`). No transform runs from the UI. |
| P2 | **Three overview actions only** — Run from ingestion · Start from step · Flush data. |
| P3 | **Uniform phase pages** — Same layout everywhere: Summary → Connectors/sources (where applicable) → Blockers → Explorer. |
| P4 | **No doctrine in operator UI** — No OCTS, legality matrices, cert packs, replay twins, readiness economics, constitutional proofs. |
| P5 | **Delete dead code with UI** — Removing a button must remove or 410 its route, task, and frontend module (no zombie APIs). |
| P6 | **Progressive depth** — Default view is childish/simple; Explorer tab holds row-level evidence. |

---

## 3. Operator mental model

### 3.1 Visible pipeline (7 steps)

The UI shows **seven operator phases**. The engine may still use internal cursors (`TRAVERSAL`, `TCRE`) — operators never name them.

```text
INGESTION → CANONICAL → IDENTITY → GRAPH → RECONSTRUCTION → RETRIEVAL → SYNTHESIS
```

| Operator label | Engine cursor(s) | What it means (one line) |
|----------------|------------------|---------------------------|
| Ingestion | (pre-FSM) | Pull raw from connectors |
| Canonical | `CANONICAL` / `CANONICAL_DRAINING` | Raw → deterministic canonical rows |
| Identity | `IDENTITY` | Orgs, people, anchors, merges |
| Graph | `GRAPH` + `TRAVERSAL` | Relationships + temporal walks (one screen) |
| Reconstruction | `TCRE` / `AWAITING_TCRE` | Execution reconstruction jobs |
| Retrieval | `RETRIEVAL` | Indexes for query/synthesis |
| Synthesis | `SYNTHESIS` | Execution summaries / artifacts |

### 3.2 Phase status vocabulary

Every phase uses the same four statuses on the overview strip:

| Status | Meaning |
|--------|---------|
| **Healthy** | Phase obligation met; no operator action required |
| **Running** | Execution lease or phase work in flight |
| **Waiting** | Upstream not ready; will proceed automatically when unblocked |
| **Blocked** | Cannot proceed; human-readable `blockers[]` required |

Optional fifth **Degraded** when work completed with known gaps (e.g. partial connector coverage) — still actionable but not hard-blocked.

---

## 4. Information architecture

### 4.1 Top navigation (final)

| Tab | Route key | Notes |
|-----|-----------|-------|
| Overview | `overview` | Pipeline strip + 3 CTAs |
| Ingestion | `ingestion` | Connectors + checkpoints + explorer |
| Canonical | `canonical` | Per-connector substrate + explorer |
| Identity | `identity` | Renamed from `entity-resolution` (redirect old URL) |
| Graph | `graph` | Merged traversal; single page |
| Reconstruction | `reconstruction` | Renamed from `reasoning` (redirect) |
| Retrieval | `retrieval` | Index health + explorer |
| Synthesis | `synthesis` | Outputs + explorer |
| Settings | `settings` | Scheduler on/off, confirmations, debug link |

### 4.2 Removed from operator nav (keep redirects or debug-only)

| Current | Action |
|---------|--------|
| Identity certification | **Delete page** — fold warnings into Identity summary |
| Traversal | **Merge into Graph** — redirect `/traversal` → `/graph` |
| Memory | **Remove** — no operator route |
| Verification (top-level) | **Remove** |
| Canonical `advanced/*` (replay, doctrine, certification, inspector, …) | **Remove from nav** — optional `/cortex/debug/...` later |
| Retrieval sub-nav (policy, provenance, replay, omissions, temporal, lineage, tcre, legality, cert pack, program closure, control-plane, …) | **Remove** |
| Synthesis sub-nav (replay, legality, runtime-legality, certification, program-closure, resynthesize, …) | **Remove** |
| Reasoning legality / certification-pack | **Remove** |
| Identity drill routes (`identity/replay-jobs`, `bundle-equivalence`, …) | **Remove from nav** — explorer replaces |

### 4.3 Debug escape hatch (not in main nav)

Optional route prefix: `/admin/tenants/:tid/cortex/debug/*`  
Re-hosts **read-only** catalog/inspect endpoints for Cursor agents. No POST mutations except via execution API. Not linked from Overview.

---

## 5. Overview page specification

**File target:** replace `frontend/src/admin/AdminCortexOverviewPage.tsx`  
**Data:** `GET …/cortex/pipeline/overview` (new) composed from execution lease + per-phase summaries

### 5.1 Layout

```
┌─────────────────────────────────────────────────────────────┐
│  PIPELINE (horizontal stepper, click → phase page)          │
│  INGESTION ✅  CANONICAL ⚠  IDENTITY ⏸  GRAPH ⏸  …         │
│  each: status icon, object count, backlog, last success     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  ATTENTION (only if blocked/degraded)                       │
│  • Retrieval blocked: graph projections missing               │
│  • Canonical backlog: 5,803 GitHub rows waiting             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  ACTIONS (exactly three)                                    │
│  [ Run from ingestion ]                                     │
│  [ Start from step ▼ ]  [ Run ]                             │
│  [ Flush data ▼ ]       [ Confirm ]                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  SCHEDULER (read-only badge + link to Settings)             │
│  Scheduled polling: ON · last tick · paused?                │
└─────────────────────────────────────────────────────────────┘
```

**Remove from Overview:** bulk sync/replay per connector, flush-rerun-to-identity, substrate completeness heatmap as primary widget, progression continue, stall recover, canonical backlog async, any "replay" wording.

### 5.2 The three actions (semantics)

#### A. Run from ingestion

**Operator intent:** Same outcome as scheduled ingestion + downstream execution — "make the workspace current."

**Implementation (engine, not UI choreography):**

1. Enqueue connector sync for all active connections (same as today's scheduler tick / manual sync-all).
2. On ingest completion, existing post-ingestion dispatch marks tenant dirty and enqueues `vector.cortex.execution.run_slice`.
3. Do **not** call deprecated `flush-rerun-to-identity`.

**API:**

```http
POST /admin/tenants/{tenant_id}/cortex/pipeline/run
{
  "mode": "from_ingestion"
}
```

**Backend handler:** `sync_all_connectors_for_tenant` + ensure dirty/enqueue (no separate Celery flush-rerun task).

#### B. Start from step

**Operator intent:** Re-run the deterministic pipeline from phase X **without** redoing earlier phases (unless flush selected).

**Dropdown values:** `canonical` | `identity` | `graph` | `reconstruction` | `retrieval` | `synthesis`  
(Not `ingestion` — use "Run from ingestion" for that.)

**API:**

```http
POST /admin/tenants/{tenant_id}/cortex/pipeline/run
{
  "mode": "from_phase",
  "start_phase": "identity"
}
```

**Maps to:** `POST …/cortex/execution/rerun?from_phase=IDENTITY` (existing M8).

#### C. Flush data

**Operator intent:** Delete derived state and optionally raw ingest, then re-run.

| UI label | `flush_mode` | Deletes | Then runs |
|----------|--------------|---------|-----------|
| Flush everything (including raw) | `all` | raw + all derived | from ingestion |
| Flush derived only (keep raw) | `derived_only` | canonical → synthesis | from canonical |

**API:**

```http
POST /admin/tenants/{tenant_id}/cortex/pipeline/run
{
  "mode": "flush_and_run",
  "flush_mode": "all" | "derived_only",
  "start_phase": "canonical"   // implied: canonical for derived_only, ingestion for all
}
```

**Maps to:** `execution/clear` + `execution/rerun` with `flush_all=true` or `from_phase=CANONICAL` (existing `clear_derived_execution_outputs_v1` / `flush_tenant_cortex_pipeline_state`).

**Safety:** Typed confirmation phrase per dangerous action (reuse `adminConstants` pattern).

### 5.3 Overview data contract

```typescript
type PhaseStatus = "healthy" | "running" | "waiting" | "blocked" | "degraded";

type PhaseOverview = {
  phase: "ingestion" | "canonical" | "identity" | "graph" | "reconstruction" | "retrieval" | "synthesis";
  status: PhaseStatus;
  processed_count: number | null;
  backlog_count: number | null;
  last_success_at: string | null;  // ISO
  blockers: string[];              // human sentences only
};

type PipelineOverview = {
  tenant_id: string;
  execution: {
    fsm_state: string;
    phase_cursor: string;
    lease_status: string;
    block_reason_code: string | null;
  };
  phases: PhaseOverview[];
  attention: string[];  // top 5 rollup blockers
};
```

**Source mapping (build in `backend/.../pipeline_admin_overview.py`):**

| Phase | Primary reads |
|-------|----------------|
| Ingestion | `build_cortex_ingestion_admin_overview` |
| Canonical | canonical health summary + backlog counts |
| Identity | identity operator summary |
| Graph | graph + traversal status aggregates |
| Reconstruction | TCRE job queue depth / failures |
| Retrieval | published index epoch + materialization status |
| Synthesis | synthesis panel / job counts |
| Execution | `build_execution_inspect_v1` / lease (authoritative) |

---

## 6. Uniform phase page specification

**Shared shell:** `frontend/src/admin/cortex/PhasePageShell.tsx` (new)

Each phase route renders:

```
┌ Header ─────────────────────────────────────────────────────┐
│ Title + one-sentence description                            │
│ Status badge · processed · backlog · last run · running?    │
└─────────────────────────────────────────────────────────────┘

┌ Sub-nav: [ Summary ] [ Explorer ] ────────────────────────┘

Summary tab:
  - Connectors table (ingestion, canonical) OR source stats (later phases)
  - Blockers list (bullets)
  - Phase-specific KPI cards (max 4)

Explorer tab:
  - Paginated table (phase-specific columns)
  - Expandable row → JSON evidence panel
```

**Phase-level CTAs:** At most **one** primary button on Summary:

| Phase | Primary CTA | Maps to |
|-------|-------------|---------|
| Ingestion | *(none — use Overview)* | — |
| Canonical | — | — |
| Identity | Rebuild identities | `rerun?from_phase=IDENTITY` |
| Graph | Rebuild graph | `rerun?from_phase=GRAPH` |
| Reconstruction | — | automatic via engine |
| Retrieval | Rebuild indexes | `rerun?from_phase=RETRIEVAL` |
| Synthesis | — | automatic via engine |

All rebuild buttons are shortcuts to Overview "Start from step" — same API, no separate bypass endpoints.

---

## 7. Per-phase content (Summary + Explorer)

### 7.1 Ingestion

**Keep**

- Connectors: rows synced, last sync, status, backlog
- Checkpoints: cursor / watermark (read-only table)
- Explorer: raw records (existing raw explorer columns)

**Remove**

- Tabs: replays, verification, coverage/exhaust, metrics dashboard as separate concepts
- Per-connector replay CTAs on Overview (ingestion sync stays in Settings or connector row "Sync now" max 1 secondary)

**Explorer columns:** `connector`, `external_id`, `ingested_at`, `payload_preview` (expand → full raw JSON)

### 7.2 Canonical

**Summary**

- Per-connector: raw rows, canonical rows, % treated, last materialization
- Global: backlog count, failure count

**Remove**

- Advanced tabs, replay drift, verification bundles, doctrine, ambiguities admin, materialize single row, backlog async task

**Explorer columns:** `canonical_type`, `source`, `entity`, `updated_at`, `status`  
Expand: raw source row, canonical payload, derivation trace (if API exists; else link to debug)

### 7.3 Identity

**Summary**

- Orgs found, people found, unresolved count, merge queue depth
- Certification warnings inline (from former certification page): e.g. "3 unresolved anchor conflicts"

**Remove**

- Readiness economics, replay jobs drill, bundle equivalence, primitives drill, authoritative-replay-async

**Explorer columns:** `kind` (person/org), `display`, `anchors`, `confidence`  
Expand: canonical evidence, merge rationale

### 7.4 Graph (includes traversal)

**Summary**

- Nodes, edges, reconstructed chains, degraded/blocked chain counts
- Blockers in plain language (no OCTS)

**Remove**

- Separate traversal tab, walk legality, readiness economics, corruption scan CTAs, purge projection buttons

**Explorer columns:** `edge_type`, `source`, `target`, `evidence`, `continuity`  
Expand: why edge exists, originating canonical refs

### 7.5 Reconstruction (was Reasoning)

**Summary**

- Queue depth, running, failed, last completed
- Recent job outcomes (status only)

**Remove**

- TCRE terminology in headings (use "Reconstruction"), legality page, certification pack, manual reconstruct bypass

**Explorer columns:** `job_id`, `status`, `created_at`, `scope`  
Expand: input artifacts, output summary

### 7.6 Retrieval

**Summary**

- Index types with coverage %, objects indexed, publish epoch
- Blockers (missing upstream, starvation)

**Remove**

- Policy, provenance, replay, omissions, temporal, lineage, tcre, degradation topology, legality, cert pack, program closure, control-plane duplicate, query debugger as default (move to debug)

**Explorer columns:** `index_type`, `coverage`, `object_count`, `status`  
Expand: index payload snippet, upstream dependencies

### 7.7 Synthesis

**Summary**

- Artifacts generated, freshness, failed generations, last run

**Remove**

- Resynthesize page, runtime legality, evaluation harness, observability catalogs

**Explorer columns:** `artifact_type`, `scope`, `created_at`, `status`  
Expand: artifact body preview

---

## 8. API layer

### 8.1 New facade (operator dialect)

**Module:** `backend/src/vector/api/http/routes/admin_cortex_pipeline.py`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `…/cortex/pipeline/overview` | Overview strip + attention |
| POST | `…/cortex/pipeline/run` | Unified run/flush (section 5.2) |
| GET | `…/cortex/pipeline/phases/{phase}/summary` | Phase summary tab |
| GET | `…/cortex/pipeline/phases/{phase}/explorer` | Paginated explorer |

Phase explorer endpoints may thin-wrap existing list APIs (ingestion raw records, canonical list, etc.) with stable column contracts.

### 8.2 Keep (read-only inspect)

| Endpoint | Use |
|----------|-----|
| `GET …/cortex/execution/state` | Debug / Settings |
| `GET …/cortex/ingestion` | Fold into overview builder |
| `GET …/cortex/substrate-completeness` | Diagnostics only (debug), not Overview hero |

### 8.3 Enforce 410 / delete (mutations)

All substrate bypass mutations listed in `CORTEX_SIMPLIFICATION_AND_DETERMINISM_REFACTOR.md` §5.2 must return **410** with `replacement: …/execution/rerun` or `…/pipeline/run`.

**High-priority removals still wired in UI today:**

| Endpoint | Frontend caller |
|----------|-----------------|
| `POST …/ingestion/actions/flush-rerun-to-identity` | `AdminCortexOverviewPage.tsx` |
| `POST …/canonical/transform/materialize` | `AdminCortexCanonicalRuntimePage.tsx` |
| `POST …/canonical/transform/materialize-backlog*` | canonical runtime/advanced |
| `POST …/retrieval/index/rebuild` | `AdminCortexRetrievalIndexPage.tsx` |
| `POST …/synthesis/jobs/run`, `resynthesize` | synthesis pages |
| `POST …/reasoning/runtime/reconstruct` | `AdminCortexReasoningOverviewPage.tsx` |
| `POST …/substrate-pipeline/progression/continue` | (if any remain) |

After UI deletion, remove handler bodies and tests that assert bypass behavior; keep 410 stubs until major version if external scripts exist.

---

## 9. Frontend deletion inventory

### 9.1 Pages to delete (or move to `cortex/debug/`)

```
AdminCortexVerificationPage.tsx
AdminCortexMemoryPage.tsx
AdminCortexIdentityCertificationPage.tsx
AdminCortexTraversalLayout.tsx
AdminCortexTraversalOverviewPage.tsx
AdminCortexTraversalControlPlanePage.tsx
AdminCortexCanonicalAdvancedLayout.tsx
AdminCortexCanonicalReplayTabPage.tsx
AdminCortexCanonicalVerificationTabPage.tsx
AdminCortexCanonicalDoctrineTabPage.tsx
AdminCortexCanonicalDebugTabPage.tsx
AdminCortexCanonicalCertificationPage.tsx
AdminCortexCanonicalControlPlanePage.tsx
AdminCortexCanonicalStabilizationPage.tsx
AdminCortexCanonicalLegacyOntologyToolsPage.tsx
AdminCortexCanonicalRegistryPage.tsx
AdminCortexCanonicalAmbiguitiesPage.tsx
AdminCortexReasoningLegalityPage.tsx
AdminCortexReasoningCertificationPackPage.tsx
AdminCortexRetrievalCatalogPage.tsx (all surfaceKey variants)
AdminCortexRetrievalLegalityPage.tsx
AdminCortexRetrievalCertificationPackPage.tsx
AdminCortexRetrievalProgramClosurePage.tsx
AdminCortexRetrievalControlPlanePage.tsx
AdminCortexRetrievalContinuityPage.tsx
AdminCortexRetrievalLineagePage.tsx
AdminCortexRetrievalQueryPage.tsx
AdminCortexRetrievalWorkflowsPage.tsx
AdminCortexRetrievalAuditPage.tsx
AdminCortexSynthesisCatalogPage.tsx (all variants)
AdminCortexSynthesisControlPlanePage.tsx
AdminCortexSynthesisResynthesizePage.tsx
AdminCortexSynthesisWorkflowsPage.tsx
AdminCortexIdentity*DrillPage.tsx (9 drill routes)
AdminCortexIdentityHandlesPage.tsx / HandleDetailPage.tsx (fold into explorer)
```

### 9.2 Files to rewrite (core)

```
AdminTenantCortexLayout.tsx       — nav + copy
AdminCortexOverviewPage.tsx       — pipeline overview only
AdminCortexIngestionPage.tsx      — summary + explorer tabs
AdminCortexCanonicalLayout.tsx    — collapse to single phase page
AdminCortexIdentityOverviewPage.tsx
AdminCortexGraphPage.tsx          — absorb traversal
AdminCortexReasoning* → Reconstruction pages (rename, slim)
AdminCortexRetrievalLayout.tsx    — two tabs only
AdminCortexSynthesisLayout.tsx    — two tabs only
main.tsx                          — route table
retrievalAdminSurfaces.ts         — delete or debug-only
synthesisAdminSurfaces.ts         — delete or debug-only
```

### 9.3 New shared components

```
frontend/src/admin/cortex/PipelineStrip.tsx
frontend/src/admin/cortex/PipelineActions.tsx
frontend/src/admin/cortex/PhasePageShell.tsx
frontend/src/admin/cortex/PhaseConnectorsTable.tsx
frontend/src/admin/cortex/PhaseBlockers.tsx
frontend/src/admin/cortex/PhaseExplorer.tsx
frontend/src/admin/cortex/pipelineTypes.ts
frontend/src/admin/cortex/usePipelineOverview.ts
```

---

## 10. Backend cleanup inventory

### 10.1 New modules

```
backend/src/vector/domains/cortex/admin/pipeline_overview.py
backend/src/vector/domains/cortex/admin/pipeline_run.py
backend/src/vector/api/http/routes/admin_cortex_pipeline.py
```

### 10.2 Celery / tasks to verify absent (already M9 target)

No admin-triggered: `cortex_canonical_materialize_backlog`, `cortex_full_pipeline_rerun`, substrate progression tick, traversal sidecars, graph density promotion.

### 10.3 Domain replay job orchestrators

Deprecate admin **enqueue** paths; keep transform functions for engine-invoked replay only:

- `canonical/replay_runtime.py` (admin run/resume → 410)
- `identity/org_link_replay_runtime.py`
- Identity `authoritative-replay-async`, `regenerate-async`

### 10.4 Tests

- Add: `test_admin_cortex_pipeline_overview.py`, `test_admin_cortex_pipeline_run.py`
- Update: `test_admin_cortex_ingestion_step6.py` (remove flush-rerun success path; assert 410)
- Delete or rewrite: frontend e2e tied to removed routes

---

## 11. Implementation waves

### Wave 0 — Plan sign-off (this document) — **Done**

- [x] **7 operator phases** — INGESTION → … → SYNTHESIS; Graph absorbs Traversal in UI (engine still runs `GRAPH` + `TRAVERSAL` cursors).
- [x] **Run from ingestion** — sync all active connectors; post-ingest `mark_dirty_and_enqueue_convergence_v1` (not flush-rerun).
- [x] **Flush labels** — `CORTEX_FLUSH_RERUN_CONFIRM_PHRASE` (all raw+derived); `CORTEX_FLUSH_DERIVED_CONFIRM_PHRASE` (derived only).
- [x] **Debug route** — **Deferred** (Wave 4+). Cursor uses existing admin read APIs; no `/cortex/debug` nav link.

#### Wave 0 decisions (§13 resolved)

| # | Decision |
|---|----------|
| 1 | Ingestion shown as **first pipeline step** (pre-FSM), not folded into Canonical. |
| 2 | **No per-connector Sync** on Overview; optional later on Ingestion connector rows only. |
| 3 | Scheduler pause/resume on **Settings** only; Overview shows read-only badge + link. |
| 4 | Graph shows **one combined status** (traversal merged into Graph nav). |
| 5 | Operator label **Reconstruction**; TCRE only in API/job payloads. |
| 6 | Debug prefix **deferred** — not in operator nav. |
| 7 | Completeness ledger **removed** from Overview hero (execution strip is primary). |
| 8 | `force` / `break_glass` — **Cursor/API only**, not operator pipeline actions. |

#### Phase status ↔ engine (operator UI)

| UI status | Engine signal |
|-----------|----------------|
| Running | Lease `RUNNING`, active `phase_cursor` / FSM |
| Waiting | `AWAITING_TCRE`, lease `WAITING` (async only) |
| Blocked | `FSM_BLOCKED`, `block_reason_code`, receipt `BLOCKED` (e.g. `topology_wait`) |
| Healthy | Phase obligation met, no blockers |
| Degraded | Completed with known gaps (partial coverage) |

### Wave 1 — P0 Surface kill — **Done**

**Goal:** Remove 70% of tabs/CTAs; wire Overview to `execution/rerun` (even before `pipeline/run` facade).

1. [x] Nav + routes per §4 (`AdminTenantCortexLayout.tsx`, `main.tsx`)
2. [x] Delete pages §9.1 (38+ frontend modules removed)
3. [x] Overview: `PipelineStrip` + `PipelineActions` → `execution/state`, `execution/rerun`, `execution/clear`
4. [x] Removed `flush-rerun-to-identity` from Overview
5. [x] Redirects: `entity-resolution`→`identity`, `reasoning`→`reconstruction`, `traversal`→`graph`, legacy sub-routes→parent
6. [x] **Kept-phase bypass cleanup (2026-05-21):** Ingestion tabs → dashboard/connectors/checkpoints/raw-explorer only; removed `trigger-replay`, verification/coverage/metrics tabs. Canonical health: read-only + link to Overview (no materialize/verification POST). Reconstruction: removed `runtime/reconstruct` and `replay-twin` CTAs; job detail shows stored diff only.

**Delivered files:** `frontend/src/admin/cortex/{pipelineTypes,pipelinePhaseStatus,PipelineStrip,PipelineActions}.tsx`, `AdminCortexSettingsPage.tsx`, slim layouts.

**Tests:** `backend/tests/vector/api/http/routes/test_admin_revamp_wave0_wave1.py` (7 static gates).

**Exit:** Operator cannot reach doctrine pages from nav; Overview has 3 POST action groups only; kept phase pages have no transform bypass POSTs (ingestion sync-only; identity `execution/rerun` shortcut allowed per §6).

### Wave 2 — P1 Pipeline API + data model — **Done**

1. [x] `GET/POST …/cortex/pipeline/overview` + `pipeline/run` (`admin_cortex_pipeline.py`, `pipeline_admin_overview.py`, `pipeline_admin_run.py`)
2. [x] `PhasePageShell` + Ingestion + Canonical migrated (`pipeline/phases/{phase}/summary|explorer`)
3. [x] `include_legacy_continuation` explicit on substrate progression GET (default `false`)

**Backend:** `backend/src/vector/domains/cortex/pipeline/*`, contracts in `admin.py`, tests `test_admin_cortex_pipeline_overview.py`, `test_admin_cortex_pipeline_run.py`.

**Frontend:** Overview + `PipelineActions` use pipeline API only; removed client-side `pipelinePhaseStatus.ts`.

**Exit:** Overview and kept phase pages use one overview contract; Overview POSTs go through `pipeline/run` only (per-connector sync remains on Ingestion rows).

### Wave 3 — P2 Remaining phases + explorers — **Done** (2026-05-21)

1. Identity, Graph (merged), Reconstruction, Retrieval, Synthesis on `PhasePageShell`
2. Shared `PhaseExplorer` — `GET …/pipeline/phases/{phase}/explorer` with pagination
3. Inline certification warnings on Identity summary (no certification tab)
4. Ingestion + Canonical migrated to `PhaseExplorer`
5. Phase CTAs via `POST …/pipeline/run` (`from_phase`) for identity, graph, retrieval only
6. Removed legacy layouts/pages, graph forensic mock stack, synthesis retry / reasoning bypass POSTs from phase UIs

**Exit:** Every phase has Summary + Explorer; ≤1 phase CTA. **Met.**

### Wave 4 — P3 Code deletion

1. Delete frontend files §9.1
2. Remove backend handlers for 410 endpoints (not just stub)
3. Remove unused admin catalog routes from OpenAPI tags
4. CI: `verify_no_admin_bypass_routes_registered_v1`

**Exit:** `rg 'materialize-backlog|flush-rerun|progression/continue'` clean in admin routes.

---

## 12. Success criteria

| Metric | Target |
|--------|--------|
| Top-level Cortex tabs | ≤9 (incl. Settings) |
| Overview POST actions | 3 |
| Phase page POST actions | ≤1 each (optional) |
| Operator-visible "replay" strings | 0 |
| Admin routes returning 200 on bypass transforms | 0 |
| Time to answer "what is blocked?" | <10s from Overview |

---

## 13. Open questions — **Resolved in Wave 0** (see table under §11 Wave 0)

---

## 14. References

| Doc / code | Relevance |
|------------|-----------|
| `DOCS/cortex/CORTEX_SIMPLIFICATION_AND_DETERMINISM_REFACTOR.md` | Execution owner, M8 API, replay matrix |
| `DOCS/cortex/CORTEX_TRUE_P0_SIGN_OFF.md` | Substrate receipts, FIFO canonical, unified dispatch |
| `backend/.../execution/admin_commands.py` | `rerun`, `clear`, phase cursor map |
| `backend/.../api/http/routes/admin_cortex_execution.py` | Current HTTP surface |
| `frontend/.../AdminTenantCortexLayout.tsx` | Current nav |
| `frontend/.../main.tsx` | Route explosion |
| `DOCS/cortex/10-admin/cortex-control-plane-overview.md` | Superseded operator model (update after sign-off) |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-21 | Initial draft from operator revamp requirements |
| 2026-05-21 | Wave 0 signed off; Wave 1 surface kill implemented (frontend + tests) |
| 2026-05-21 | Wave 1 gap closure: ingestion/canonical/reconstruction bypass CTAs removed; static test gates extended |
| 2026-05-21 | Wave 2: pipeline overview/run API, PhasePageShell, Ingestion + Canonical migration |
| 2026-05-21 | Wave 3: all seven phase pages, `pipeline_phase_views` summary/explorer, `PhaseExplorer`/`PhaseRerunCta`, dead UI removed |
