# Cortex Admin — Full Refactor Plan (v1)

**Status:** Implementation plan — no code yet  
**Date:** 2026-05-24  
**Grounding:** [`cortex_admin_full_reality_audit_v1.md`](../audits/cortex_admin_full_reality_audit_v1.md), [`cortex_full_system_reality_audit_2026-05-24.md`](../audits/cortex_full_system_reality_audit_2026-05-24.md)  
**Prod anchor:** Fizzer `c08ef32b-f89a-40f6-9566-e19b5329436f` (7,393 entities, 96% isolated, phase 07 fail-loud, 1043 failed synthesis jobs)

**Product thesis:** The admin is an **execution observability console**. Operators see **facts and chains**, not KPI soup. They answer: *who is this person across systems, what execution thread is alive, what was retrieved, what was synthesized, and why is it blocked.*

**Non-goals:** Ontology dashboards, doctrine catalogs in UI, semantic readiness hero panels, 7 phase vanity tabs, live connected-component scans on navigation.

---

# Section 1 — Target Admin Information Architecture

## 1A. Final tab model (5 tabs)

| Tab | Route | Type | Load on entry | Purpose |
|-----|-------|------|---------------|---------|
| **Overview** | `/cortex` (index) | Operational | **1 GET** | Blocked-because, continuity facts, recent events, primary actions |
| **Runtime** | `/cortex/runtime` | Operational | **1 GET** | Lease truth, transition timeline, lanes, queues, replay controls |
| **Inspect** | `/cortex/inspect` | Inspector hub | **0 GET** (shell only) | Pick inspector → lazy load evidence chains |
| **Queues** | `/cortex/queues` | Operational | **1 GET** | Deferrals, failed jobs, TCRE queue, ingestion backlog — actionable lists |
| **Settings** | `/cortex/settings` | Config | **1 GET** | Scheduler, connector routing, env flags (read-only display) |

**Removed entirely (no redirects after migration window):**

| Old tab | Fate |
|---------|------|
| Ingestion | **Merge** → Overview (connector facts) + Queues (runs list) + Inspect (raw explorer) |
| Canonical | **Delete** tab — deferral/retry facts on Queues; canonical lane on Runtime |
| Identity | **Delete** tab — Inspect → Identity |
| Graph | **Delete** tab — Inspect → Graph / Islands |
| Reconstruction | **Delete** tab — Inspect → Execution thread + job detail deep links |
| Retrieval | **Delete** tab — Inspect → Retrieval lineage |
| Synthesis | **Delete** tab — Inspect → Synthesis evidence + job debugger |

Legacy URL redirects (30-day): `/cortex/graph?inspector=identity` → `/cortex/inspect/identity`, etc.

## 1B. Page relationship diagram

```
                    ┌─────────────┐
                    │  Overview   │  ← "What is blocked? What happened recently?"
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │  Runtime   │  │   Queues   │  │  Inspect   │
    │ lease/FSM  │  │ lists/jobs │  │ evidence   │
    │ timeline   │  │ failures   │  │ chains     │
    └────────────┘  └────────────┘  └────────────┘
           │               │               │
           └───────────────┴───────────────┘
                           │
                    POST /operator/actions
                    (replay, flush, rerun)
```

- **Overview** links into Inspect with context (`?entity=`, `?island=`, `?epoch=`, `?job=`).
- **Runtime** is where destructive actions live (confirmations, audit trail).
- **Inspect** never loads on layout mount — user picks a lens.
- **Queues** is for *lists you act on* (retry, open job, replay island).
- **Settings** is global/tenant config only — no pipeline truth.

## 1C. Operator flows (primary journeys)

### Journey A — "Why is Cortex stuck?" (daily)

1. Open Overview → read **Blocked because** line (from lease `block_reason_code` + last phase receipt).
2. Scan **Continuity facts** (5 one-liners: ingestion, execution, graph, retrieval, synthesis).
3. If needed → Runtime → transition timeline (last 20 events with timestamps).
4. Act: Run from phase / Flush derived (Runtime actions panel).

### Journey B — "Is Slack user X the same as GitHub user Y?"

1. Inspect → Identity → search Slack user id / GitHub login / email.
2. Click entity → **Entity continuity card** (existing `build_identity_continuity_entity_inspector_v1`).
3. See: linked handles, promotion lineage, rule_id per edge, evidence raw record ids.

### Journey C — "Was this PR retrieved and synthesized?"

1. Inspect → Retrieval → search by scope ref (PR id, task id, entity id).
2. See: index entry row, epoch, index_kind, lineage chain (terminal→root).
3. Click through → Synthesis evidence → job/artifact with claim text + retrieval pin refs.

### Journey D — "Is this island alive?"

1. Inspect → Islands → list from **registry snapshot** (not live component scan).
2. Click island → scope id, entity ids (sample), last retrieval epoch, last walk, synthesis status.
3. Action: Rebuild island (queue job) from Runtime/Queues.

## 1D. Tab load classification

| Surface | Always-live | Cached (60s) | Background snapshot | Async job |
|---------|-------------|--------------|---------------------|-----------|
| Overview | lease row, block_reason | connector last-sync, queue counts | — | — |
| Runtime | lease, transitions (paginated) | dual-lane inspect | — | — |
| Queues | deferral counts, job lists (paginated) | — | — | — |
| Inspect shell | — | — | — | — |
| Inspect: entity | entity + links (on open) | — | — | — |
| Inspect: islands | — | — | registry + component snapshot | refresh components |
| Inspect: graph summary | — | — | materialized graph snapshot | — |
| Settings | scheduler pause flag | connector list | — | — |

---

# Section 2 — Overview Redesign

## 2A. Design intent

**Operator feeling on open:** Within 300ms (warm) / 1s (cold), they see:

1. **One sentence:** what the worker is doing or why it stopped.
2. **Five continuity facts** — not scores, not badges — plain language with **evidence links**.
3. **Recent events** — last 5 things that actually happened (sync, transition, phase fail, epoch publish).
4. **Two buttons** — Run / Inspect — not a control panel of 12 actions.

No KPI cards. No semantic panel. No phase strip with 7 colored pills. No deferral doctrine essay.

## 2B. Exact sections (top to bottom)

### Section 1 — Status banner (full width)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ EXECUTION PAUSED · phase 07 retrieval · blocked: retrieval_semantic_mix  │
│ Canonical lane: waiting (topology_wait) · Execution lane: dirty            │
│ Last transition: 2026-05-24 10:06 UTC · cursor unchanged since 6h        │
│ [Open Runtime →]                                                         │
└──────────────────────────────────────────────────────────────────────────┘
```

**Data source:** `lease` row only (+ `last_transition_at` from transition log LIMIT 1).

**No** derived `continuity_status.state` enum. Display raw lease fields; humanize labels in frontend.

### Section 2 — Continuity facts (5 rows, not cards)

Each row = one sentence + link to Inspect. **Not numbers unless the fact is a count that matters.**

| Row | Example copy (Fizzer) | Source | Link |
|-----|----------------------|--------|------|
| Ingestion | "Notion synced 2h ago; Slack/GitHub stale >24h" | connector last_run timestamps | Inspect → Ingestion sources |
| Execution | "Worker dirty; last slice failed at retrieval mix gate" | lease + last transition | Runtime |
| Graph | "297 entities in auth graph; Slack/GitHub not linked yet" | snapshot `entities_in_graph`, promotable-by-rule | Inspect → Identity |
| Retrieval | "Last publish failed; prior epoch 100% org_link (stale 24h)" | phase 07 receipt + epoch metadata | Inspect → Retrieval |
| Synthesis | "No published claims; 1043 failed jobs in backlog" | synthesis job counts | Queues → Failed synthesis |

**Data source:** `GET …/cortex/operator/overview` — precomputed strings server-side from lease + receipts + **materialized snapshot** (not live semantic bundle).

### Section 3 — Recent events (timeline, max 10)

Unified feed merging:

- Last 3 ingestion runs (connector, status, time)
- Last 5 execution transitions (from_phase → to_phase, outcome)
- Last published/failed epoch event (if any)

**Not** a metrics chart. Click row → Runtime or Inspect.

### Section 4 — Actions (compact)

- **Run from ingestion** (if connectors runnable)
- **Run from phase** (dropdown: canonical … synthesis)
- **Open Inspect**

Destructive flush → Runtime tab only.

### Section 5 — Connectors (table, not cards)

| Connector | Last sync | Status | Action |
|-----------|-----------|--------|--------|
| notion | 2h ago | ok | Sync now |
| slack | 3d ago | stale | Sync now |
| github | 3d ago | stale | Sync now |

**Data:** subset of existing `build_cortex_ingestion_admin_overview(lite=True)` — no raw row counts, no duplicate-scan.

## 2C. Fetch strategy

```
GET /admin/tenants/{id}/cortex/operator/overview
```

**Single request.** Target p95 < 500ms on Fizzer.

**Backend builder:** `build_operator_overview_v1` (new, replaces bootstrap).

**Queries (hard cap 8):**

1. `get_tenant_execution_lease_v1` — 1 row
2. `SELECT … FROM cortex_execution_transition_log ORDER BY created_at DESC LIMIT 1`
3. Connector + latest run per connector (existing ingestion admin lite path, no raw counts)
4. `list_recent_ingestion_runs(limit=3)`
5. Last terminal receipt per critical phase (07, 08) — indexed lookup on `cortex_substrate_phase_runs`, not full progression build
6. Queue counts: `retry_ready` deferrals, `synthesis failed` count, `tcre queued` count — 3 cheap COUNTs
7. Read **materialized snapshot** row: `cortex_admin_continuity_snapshot` (graph/retrieval one-liners)
8. Scheduler pause flag (Redis or settings)

**Explicitly NOT called:**

- `build_continuity_overview_context_v1`
- `build_continuity_phase_cards_v1`
- `build_semantic_readiness_v1`
- `build_operator_primary_kpi_v1`
- `list_graph_connected_components_v1`

## 2D. Cache strategy

| Layer | Mechanism |
|-------|-----------|
| API | In-process 30s TTL keyed `{tenant_id}:operator_overview` |
| Shared | Optional Redis 30s for multi-pod (phase R4+) |
| Snapshot | DB row refreshed every 5–15m or post-phase-terminal |
| Frontend | React Query `staleTime: 30_000`, `retry: 0`, single key per tenant |

**Invalidation:** POST `/operator/actions` and successful connector sync invalidate overview + runtime keys only — not entire cortex cache forest.

## 2E. What disappears from Overview UI

Delete components (frontend):

- `SemanticReadinessCard.tsx`
- `OperatorPrimaryKpiCard.tsx`
- `DeferralOmissionCard.tsx`
- `OperationalPhaseStrip.tsx` / `PipelineStrip.tsx` (7-phase model)
- `ContinuityStatusCard.tsx` (replace with status banner)

---

# Section 3 — Runtime Tab

## 3A. Purpose

Answer: *What is the worker doing right now, what did it do recently, and how do I intervene?*

This is **not** another dashboard. It is a **log + state inspector** with actions attached.

## 3B. Layout

### Block 1 — Lease truth (read-only facts)

Display lease row fields verbatim:

- `fsm_state`, `phase_cursor`, `status`, `obligation_epoch`, `target_epoch`
- `block_reason_code`, `block_detail` (expandable JSON)
- `canonical_lane` / `execution_lane` from `build_dual_lane_inspect_v1`
- `pipeline_run_id` (link to substrate run if we keep detail page)

**Source:** Wire existing `build_execution_inspect_v1` — today unused by UI.

### Block 2 — Transition timeline (paginated)

Table: `time | event | from → to | outcome | detail`

- Source: `CortexExecutionTransitionLog`, default 50, load-more
- Click row → expand `detail_json`
- **No** aggregation, **no** charts

### Block 3 — Lanes (dual-lane inspect)

Show canonical vs execution lane last outcomes from `build_dual_lane_inspect_v1`:

- Last canonical outcome (`topology_wait`, etc.)
- Last execution phase reached
- **Fact strings**, not health badges

### Block 4 — Queue hints (links to Queues tab)

- Retry-ready deferrals: N → Queues
- TCRE queued: N → Queues
- Synthesis failed: N → Queues

Counts only — detail lists live on Queues.

### Block 5 — Operator actions

Unified panel (see Section 6 backend):

| Action | Confirmation | Effect |
|--------|--------------|--------|
| Run from phase | none | enqueue convergence |
| Restart execution | phrase | `restart_execution_from_phase_v1` |
| Clear derived | phrase | `clear_derived_execution_outputs_v1` |
| Flush all | strong phrase | `flush_tenant_cortex_pipeline_state` |
| Rebuild retrieval index | phrase | enqueue index bootstrap job |
| P0 recover | phrase | `recover_continuity_p0_pipeline_v1` |

Each action → audit log row + invalidate overview/runtime.

## 3C. Fetch strategy

```
GET /admin/tenants/{id}/cortex/operator/runtime?transition_limit=50&transition_offset=0
```

Wraps `build_execution_inspect_v1` with pagination on transitions.

**Do not** embed island registry full scan on every load — link to Inspect → Islands.

**Cache:** 15s TTL. Transitions are live; short cache prevents stampede on tab flip.

## 3D. Avoiding ontology dashboard drift

**Banned on Runtime tab:**

- AA proof panel scores
- Operational maturity cards
- Certification packs
- Doctrine copy blocks

Those stay in CI/docs, not operator UI.

---

# Section 4 — Inspector System

## 4A. Inspector hub UX

```
/cortex/inspect                    → lens picker (no fetch)
/cortex/inspect/identity           → search UI
/cortex/inspect/identity/e/{id}    → entity card
/cortex/inspect/graph              → graph snapshot + edge search
/cortex/inspect/islands            → island list
/cortex/inspect/islands/{scopeId}  → island detail
/cortex/inspect/retrieval          → epoch + entry search
/cortex/inspect/retrieval/lineage  → chain for lookup id
/cortex/inspect/synthesis          → job/artifact search
/cortex/inspect/execution          → thread search (PR/task/walk)
```

**Hub page:** static lens cards with description — zero API calls.

**Rule:** Opening Inspect never triggers graph component scan. User action required.

## 4B. Inspector catalog

| Inspector | User question | API | Load | Async |
|-----------|---------------|-----|------|-------|
| **Identity** | Who is this person across systems? | Existing search + entity inspector | On search / entity click | No |
| **Graph** | Why does this edge exist? | New: edge lookup + rule provenance | On search | Snapshot for summary |
| **Islands** | What execution scopes are alive? | Registry list + snapshot detail | List on tab open; detail on click | Component refresh job |
| **Retrieval** | Was this PR indexed? | Epoch list + entry search + lineage chain | On search | No |
| **Synthesis** | What claim came from which retrieval? | Job list + debugger + artifact pins | On search | No |
| **Execution thread** | What walk/TCRE/index chain for this scope? | Walk replay lineage + TCRE job + index entries | On search | No |

## 4C. UX patterns (evidence-first)

### Pattern: Search → Result list → Detail drawer

Used for: identity, retrieval entries, synthesis jobs, edges.

- Result row shows **identifiers** (Slack user id, GitHub login, PR url, entity id) — not counts.
- Detail drawer shows **chain** vertically:

```
Anchor (slack user U123)
  → promoted edge (rule: slack_user_id_v1, batch: …, evidence: raw#9982)
    → org entity (uuid)
      → auth edge (rule: github_login_v1)
        → GitHub user entity
          → retrieval index entry (epoch-57147…, kind: walk)
            → synthesis artifact (job …, claim: "…")
```

### Pattern: Snapshot + stale badge

Graph summary and island component sizes read from `cortex_admin_graph_snapshot`:

- Show `captured_at_utc`
- If age > 15m: "Snapshot stale · [Refresh]" → POST async job

### Pattern: Fact row (not KPI card)

Instead of `unique_auth_pairs: 2080`, show:

> "Auth graph connects 297 of 7,393 entities (4%). Largest component: 285 entities. [See isolated entities →]"

## 4D. Lazy vs eager

| Inspector | Eager | Lazy |
|-----------|-------|------|
| Hub | — | always |
| Identity search | — | on submit |
| Entity card | — | on entity select |
| Graph snapshot summary | on tab open (from materialized row) | edge search |
| Islands list | on tab open (registry table) | component sizes async |
| Retrieval epochs | on tab open (last 5 epochs list) | entry/lineage search |
| Synthesis | — | on search |
| Execution thread | — | on scope id search |

## 4E. Reuse existing backend (wire, don't rewrite)

| Inspector | Keep / wire |
|-----------|-------------|
| Identity search | `resolve_continuity_search_v1`, routes in `admin.py` |
| Entity card | `build_identity_continuity_entity_inspector_v1` |
| Synthesis debugger | `build_synthesis_job_debugger_v1`, existing job detail page |
| Reasoning job | `operator-view` route, existing page (link from Inspect) |
| Retrieval lineage | `build_retrieval_lineage_explorer_chain_v1` — wire to Inspect |
| Walk lineage | `list_walk_replay_lineage_v1` |
| Island registry | `list_execution_island_registry_v1` — list only, no inspect sync on load |

**Replace / narrow:**

- `graph-truth-inspector` → split into snapshot (background) + edge lookup (on demand)
- `semantic-readiness` → delete from UI; fold into snapshot writer offline

---

# Section 5 — Graph / Identity Observability

## 5A. Problem statement (Fizzer)

Operators cannot trust the graph because they only see aggregates:

- 96% isolated reads as "graph broken" but doesn't show **which** Slack users lack GitHub links
- 2,080 auth edges are all Notion-handle star — no UI shows "17 personas → 293 handles"
- Promotion rules: Notion + email only — Slack/GitHub promotable counts are zero but hidden in semantic panel

**Goal:** Prove "graph is graphing" by showing **missing links** and **successful links** as navigable evidence.

## 5B. Identity continuity observability

### Surface: Identity search (existing, promoted to first-class)

Search keys: `slack_user_id`, `github_login`, `email`, `notion_user_id`, `entity_id`, `canonical_entity_id`

**Result:** list of matching entities with **linked systems** column:

| Entity | Systems seen | In auth graph? |
|--------|--------------|----------------|
| uuid… | Slack, Notion | yes |
| uuid… | GitHub only | no |

### Surface: Entity continuity card (existing `IdentityEntityCard.tsx`, enhance)

Show **facts**:

- Resolved identities (Slack handle, GitHub login, email) — from `linked_handles`, `resolved_identities`
- **Promotion lineage** table: candidate → rule_id → batch → promoted link id
- **Authoritative links** with `rule_id`, `link_type`, counterpart entity (clickable)
- **Skipped candidates** with `skip_reason_code` — explains why Slack→GitHub didn't promote
- Evidence: raw record ids (link to raw explorer in Inspect, paginated)

**Fizzer example copy:**

> "Entity `a1b2…` is anchored to Notion user `xyz`. Has 12 candidate Slack pairs; 0 promotable under `slack_user_id_v1` (missing anchor evidence). GitHub login `octocat` not linked."

### Surface: Cross-system chain view (new UI, existing data)

When entity has multiple handles, render horizontal chain (not graph viz):

`Slack U123 ──(candidate, skipped: no_evidence)──×── GitHub octocat`

Successful chain:

`Slack U456 ──(promoted, rule slack_user_id_v1)── Entity ──(email rule)── Entity ── GitHub octocat`

**Backend:** compose from entity inspector payload — no new graph scan.

## 5C. Graph truth observability

### Surface: Graph snapshot (materialized, not live)

Background job every 10m or post-phase-04/05 terminal writes:

```json
{
  "captured_at_utc": "...",
  "active_entities": 7393,
  "entities_in_auth_graph": 297,
  "isolated_entities": 7096,
  "unique_auth_pairs": 2080,
  "dup_factor": 1.0,
  "promotions_by_rule": [{"rule_id": "...", "unique_pairs": 2000}],
  "top_link_types": [{"link_type": "org.persona_belongs_to_handle", "count": 2000}],
  "promotable_slack": 0,
  "promotable_github": 0,
  "largest_component_size": 285,
  "component_count": 42
}
```

**UI:** prose summary + tables — not six KPI tiles.

### Surface: Edge provenance lookup (on demand)

```
GET /admin/tenants/{id}/cortex/inspect/edges?source={id}&target={id}&link_type=
```

Returns: link row, `rule_id`, `promoted_from_candidate_id`, batch, created_at, revoked_at.

**Fizzer use:** "Why does persona X belong to handle Y?" → show `p04.candidate.exact_notion_user_id_v1`.

### Surface: Islands (registry-first)

List from `cortex_execution_island_registry` (already persisted):

| Island scope | Entities | Last retrieval epoch | Last walk | Synthesis |
|--------------|----------|----------------------|-----------|-----------|

Click → island detail: sample entity ids (20), scope boundary explanation, link to retrieval epoch.

**Component size distribution:** async snapshot only — button "Compute components" triggers job, poll status.

## 5D. Proving "graph is graphing"

Operator checklist (UI renders pass/fail from snapshot + lease):

| Check | Fizzer today | UI fact |
|-------|--------------|---------|
| Any cross-system promotion? | email rule only | Show rule list |
| Slack/GitHub promotable > 0? | 0 | Red fact + link to skipped candidates |
| Entities in graph growing week/week? | flat | Snapshot delta (if we store history) |
| Retrieval references auth edges? | org_link mirror | Link to retrieval inspector |
| Islands with retrieval epoch? | some | Island table |

**No single "graph health score".** List of pass/fail facts with drill-down.

---

# Section 6 — Retrieval / Synthesis Observability

## 6A. Design principle

Show **indexed objects and chains**, not mix percentages as hero metrics.

Mix ratio appears as **one fact line** inside retrieval continuity row, not a dashboard.

## 6B. Retrieval inspector

### Epoch list (on tab open)

Last 5 published/failed epochs:

| Epoch | Published | Entry count | Mix note | Action |
|-------|-----------|-------------|----------|--------|
| epoch-57147… | yes | 1599 | 100% org_link | Inspect |
| (failed) | no | — | semantic_mix_violation | View error |

**Source:** `cortex_retrieval_index_epochs` — indexed, cheap.

### Entry search (on demand)

Search by: `entity_id`, `scope_ref`, `index_kind`, `walk_id`, `external_url` (PR)

Result row: entry id, kind, epoch, created_at, scope summary.

### Lineage chain (on row click)

Wire existing:

```
GET …/cortex/retrieval/lineage/{kind}/{ref}
→ build_retrieval_lineage_explorer_chain_v1
```

UI: vertical chain terminal→root with hop labels (org_link → walk → causal_chain → …).

**Fizzer example:**

> PR `#42` → indexed as `org_link` only → lineage stops at Notion handle → **no walk edge** → explains weak synthesis.

## 6C. Synthesis inspector

### Job search

Paginated failed/recent jobs:

| Job | Status | Created | Error / scope | Action |
|-----|--------|---------|---------------|--------|

**Source:** `cortex_synthesis_jobs` WHERE tenant — indexed status + created_at.

Click → existing **job debugger** page (`AdminCortexSynthesisJobDetailPage.tsx`) — keep, link from Inspect.

### Artifact evidence (on demand)

For published artifact:

- Claims list (text snippets)
- Retrieval plan pins (which index entries)
- Scope id / island id
- LLM model route (metadata only)

**Source:** `build_synthesis_job_debugger_v1` + artifact body_json.

### Grounding chain UI

```
Retrieval entry (walk-abc)
  → synthesis job (job-xyz)
    → artifact claim: "Deployment blocked because …"
      → evidence refs: [raw#..., edge#...]
```

**No "published claims 7d" KPI.** Show last 3 artifacts with titles/claims or "none".

## 6D. Failed job observability (Queues tab overlap)

Queues tab lists:

- Synthesis failed (paginated, 50)
- TCRE queued/stuck
- Ingestion runs failed (recent)

Click → Inspect detail or Runtime context.

---

# Section 7 — Backend Refactor Plan

## 7A. New API surface (target)

All under `/admin/tenants/{tenant_id}/cortex/operator/`:

| Method | Path | Builder | Replaces |
|--------|------|---------|----------|
| GET | `/overview` | `build_operator_overview_v1` | bootstrap, monolith, slices |
| GET | `/runtime` | `build_operator_runtime_v1` | execution/state + inspect wrapper |
| GET | `/queues` | `build_operator_queues_v1` | scattered counts |
| POST | `/actions` | `execute_operator_action_v1` | pipeline/run + execution/* POSTs |
| GET | `/snapshots/graph` | read materialized row | semantic-readiness graph section |
| POST | `/snapshots/graph/refresh` | enqueue Celery job | live component scan |
| GET | `/inspect/edges` | `lookup_edge_provenance_v1` | graph-truth-inspector |
| GET | `/inspect/islands` | `list_execution_island_registry_v1` | island inspect sync |
| GET | `/inspect/islands/{scope}` | `build_island_detail_v1` | new narrow query |

**Keep unchanged (wire to Inspect):**

- `…/cortex/identity/continuity-inspector/*` (search, entity, evidence)
- `…/cortex/retrieval/lineage/*`
- `…/cortex/synthesis/jobs/{id}/debugger`
- `…/cortex/reasoning/runtime/jobs/{id}/operator-view`
- `…/cortex/ingestion/recent-runs`, `trigger-sync`
- `…/cortex/ingestion/actions/*`

## 7B. Delete (route modules / handlers)

| Target | Action |
|--------|--------|
| `GET …/pipeline/overview` | DELETE after migration |
| `GET …/pipeline/overview/bootstrap` | DELETE |
| `GET …/pipeline/overview/{execution,phases,ingestion}` | DELETE |
| `GET …/pipeline/semantic-readiness` | DELETE from UI path; keep internal for snapshot writer only |
| `GET …/pipeline/graph-truth-inspector` | DELETE — replace with snapshot + edge lookup |
| `GET …/pipeline/identity-continuity-inspector` | DELETE duplicate if entity routes suffice |
| `GET …/pipeline/phases/{phase}/summary-detail` | DELETE — receipts on overview/runtime |
| Legacy `/cortex/overview/*` aliases | DELETE |
| `admin_cortex_operational_runtime.py` tenant routes (~70) | DELETE or `@deprecated` hidden |
| `admin_cortex_retrieval.py` catalog GETs (~25) | DELETE catalogs; keep lineage, query, health |
| `admin_cortex_synthesis.py` catalog GETs (~20) | DELETE catalogs; keep jobs/debugger |
| `admin.py` memory/certification/control-plane routes | DELETE from cortex UI scope |

## 7C. Collapse context builders

**DELETE as admin entry points:**

- `build_pipeline_overview_bootstrap_v1`
- `build_pipeline_overview_v1` / `_uncached`
- `build_pipeline_overview_{execution,phases,ingestion}_v1`
- `_cached_continuity_bundle_v1` (slice-specific)
- `build_continuity_overview_bundle_v1` for overview (keep narrow parts for snapshot writer if needed)
- `build_operator_primary_kpi_v1` for overview path
- `build_semantic_readiness_admin_v1` on request path

**KEEP and call from new builders:**

| Function | Used by |
|----------|---------|
| `get_tenant_execution_lease_v1` | overview, runtime |
| `build_dual_lane_inspect_v1` | runtime |
| `build_execution_inspect_v1` | runtime (narrowed — drop heavy embeds optional) |
| `build_cortex_ingestion_admin_overview(lite=True)` | overview connectors |
| `list_recent_ingestion_runs` | overview events |
| `count_deferrals` | queues |
| `build_identity_continuity_entity_inspector_v1` | inspect |
| `resolve_continuity_search_v1` | inspect |
| `list_execution_island_registry_v1` | inspect islands |
| `build_retrieval_lineage_explorer_chain_v1` | inspect retrieval |
| `build_synthesis_job_debugger_v1` | inspect synthesis |
| `pipeline_run_v1` logic | merged into `execute_operator_action_v1` |

## 7D. Materialized snapshots (new DB)

### Table: `cortex_admin_continuity_snapshot`

| Column | Purpose |
|--------|---------|
| tenant_id | PK |
| captured_at_utc | |
| graph_summary_json | entities in graph, isolation, promotable slack/github, top rules |
| retrieval_summary_json | last epoch, mix, freshness, last error |
| synthesis_summary_json | failed count, last artifact summary |
| identity_summary_json | anchors missing, open ambiguities |
| schema_version | |

**Writer:** Celery task `refresh_admin_continuity_snapshot_task` — triggered post-phase-terminal (03–08), every 10m beat, manual refresh in Inspect.

**Reader:** `build_operator_overview_v1` — 1 SELECT, no aggregations.

### Table: `cortex_admin_graph_component_snapshot` (optional phase R3)

| Column | Purpose |
|--------|---------|
| tenant_id, captured_at_utc | |
| component_count | |
| component_sizes_top_20 | jsonb |
| job_status | pending/running/complete/failed |

Populated only by async job (`list_graph_connected_components_v1`).

## 7E. Unified cache

Replace 7 in-process caches with:

| Key | TTL | Notes |
|-----|-----|-------|
| `operator:overview:{tenant}` | 30s | single overview cache |
| `operator:runtime:{tenant}` | 15s | |
| `operator:queues:{tenant}` | 30s | |
| `inspect:entity:{tenant}:{id}` | 60s | |
| `ingestion:connectors:{tenant}` | 30s | shared ingestion lite |

**Delete:** `_SLICE_CACHE`, `_OVERVIEW_CACHE`, `_CONTINUITY_CONTEXT_CACHE` (admin path), `_SEMANTIC_CACHE`, `_GRAPH_TOPOLOGY_CACHE` (admin path).

Singleflight: only on snapshot refresh job, not on HTTP request path.

## 7F. Contract simplification

New Pydantic module: `vector/contracts/operator_admin.py` (~200 lines)

- `OperatorOverviewResponse`
- `OperatorRuntimeResponse`
- `OperatorQueuesResponse`
- `OperatorActionRequest` / `OperatorActionResponse`
- `GraphSnapshotResponse`

**Stop extending** `admin.py` 5000-line contracts for operator surfaces.

## 7G. Dependency graph (target)

```
HTTP
 └─ operator/overview
      ├─ lease (1 query)
      ├─ transition tail (1 query)
      ├─ ingestion lite (2–3 queries)
      ├─ phase receipts (2 queries)
      ├─ queue counts (3 queries)
      └─ continuity_snapshot (1 SELECT)

HTTP
 └─ operator/runtime
      └─ build_execution_inspect_v1 (bounded)

HTTP
 └─ inspect/*
      └─ narrow inspectors (existing builders)

Background
 └─ refresh_admin_continuity_snapshot_task
      ├─ snapshot_authoritative_link_topology_v1
      ├─ promotable counts (try/except)
      ├─ epoch mix
      └─ synthesis counts
      (NO component scan in default writer)

Background (on demand)
 └─ refresh_graph_components_task
      └─ list_graph_connected_components_v1
```

---

# Section 8 — Frontend Refactor Plan

## 8A. Route structure

Replace `frontend/src/main.tsx` cortex routes with:

```
/admin/tenants/:tenantId/cortex                    → OperatorOverviewPage
/admin/tenants/:tenantId/cortex/runtime            → OperatorRuntimePage
/admin/tenants/:tenantId/cortex/queues             → OperatorQueuesPage
/admin/tenants/:tenantId/cortex/inspect            → InspectorHubPage
/admin/tenants/:tenantId/cortex/inspect/:lens      → InspectorLensPage
/admin/tenants/:tenantId/cortex/inspect/:lens/*    → nested detail routes
/admin/tenants/:tenantId/cortex/settings           → OperatorSettingsPage
/admin/tenants/:tenantId/cortex/jobs/synthesis/:id → keep existing debugger
/admin/tenants/:tenantId/cortex/jobs/reasoning/:id → keep existing operator view
```

## 8B. Layout change

**Delete:** `usePrefetchPipelineOverviewBootstrap()` from layout — **no prefetch on navigation**.

Overview page owns its single fetch. Other tabs own theirs. No layout-level pipeline fetch.

**New layout:** `AdminTenantCortexLayout.tsx` — tabs only + outlet. Zero data fetching.

## 8C. React Query strategy

### Query keys (canonical)

```typescript
export const operatorKeys = {
  overview: (tenantId: string) => ["cortex-operator-overview", tenantId] as const,
  runtime: (tenantId: string, offset: number) => ["cortex-operator-runtime", tenantId, offset] as const,
  queues: (tenantId: string, tab: string) => ["cortex-operator-queues", tenantId, tab] as const,
  snapshot: (tenantId: string, kind: string) => ["cortex-snapshot", tenantId, kind] as const,
  inspect: {
    entity: (tenantId: string, entityId: string) => ["cortex-inspect-entity", tenantId, entityId] as const,
    search: (tenantId: string, params: IdentitySearchParams) => ["cortex-inspect-search", tenantId, params] as const,
    lineage: (tenantId: string, kind: string, ref: string) => ["cortex-inspect-lineage", tenantId, kind, ref] as const,
    islands: (tenantId: string) => ["cortex-inspect-islands", tenantId] as const,
  },
};
```

### Defaults

| Query | staleTime | retry | enabled |
|-------|-----------|-------|---------|
| overview | 30s | 0 | on mount |
| runtime | 15s | 0 | on mount |
| queues | 30s | 0 | on mount |
| inspect * | 60s | 0 | user action |
| job detail | 45s | 1 | on mount |

### Delete hooks/files

- `fetchPipelineOverviewSlice.ts` (monolith fallback, slice storm)
- `usePipelineOverview.ts` (all slice hooks)
- `usePhaseSummaryDetail.ts`
- `PhasePageShell.tsx`
- `useGraphTruthInspector.ts` (replace with inspect-specific hooks)
- All `AdminCortex*Page.tsx` phase pages except job detail pages

### New fetch module

`frontend/src/admin/operator/fetchOperator.ts` — thin wrappers, **no module-level inflight dedup** (React Query handles dedup).

**No monolith fallback.** If endpoint 404, show deploy version mismatch banner.

## 8D. Invalidation model

```typescript
export function invalidateOperatorCaches(queryClient, tenantId: string) {
  queryClient.invalidateQueries({ queryKey: ["cortex-operator-overview", tenantId] });
  queryClient.invalidateQueries({ queryKey: ["cortex-operator-runtime", tenantId] });
  queryClient.invalidateQueries({ queryKey: ["cortex-operator-queues", tenantId] });
}
```

Called after:

- POST `/operator/actions`
- POST trigger-sync
- Scheduler pause

**Do not** invalidate inspect entity caches on every action — only affected entity if known.

## 8E. Error handling

- Overview failure: full-page error with lease unavailable message + retry button — not scattered "Failed to fetch" cards.
- Inspect failure: inline error in drawer, rest of hub usable.
- Stale snapshot: yellow banner with age + refresh — not silent old data.

## 8F. Component architecture

```
frontend/src/admin/operator/
  OperatorOverviewPage.tsx
  OperatorRuntimePage.tsx
  OperatorQueuesPage.tsx
  OperatorSettingsPage.tsx
  components/
    StatusBanner.tsx
    ContinuityFactList.tsx
    RecentEventsTimeline.tsx
    ConnectorTable.tsx
    TransitionTimeline.tsx
    ActionPanel.tsx
  inspect/
    InspectorHubPage.tsx
    InspectorLensPage.tsx
    identity/IdentitySearch.tsx, EntityContinuityDrawer.tsx
    graph/GraphSnapshotSummary.tsx, EdgeLookup.tsx
    islands/IslandList.tsx, IslandDetail.tsx
    retrieval/EpochList.tsx, EntrySearch.tsx, LineageChain.tsx
    synthesis/JobSearch.tsx
    execution/ThreadSearch.tsx
  hooks/
    useOperatorOverview.ts
    useOperatorRuntime.ts
    useOperatorQueues.ts
    useInspect*.ts
  fetchOperator.ts
  types.ts
```

Reuse where possible:

- `IdentityEntityCard.tsx` → entity drawer
- `IngestionRunsTable.tsx` → queues ingestion section
- `PipelineActions.tsx` → refactor to `ActionPanel.tsx` using `/operator/actions`

---

# Section 9 — DELETE / KEEP / SIMPLIFY Matrix

| Path | Verdict | Notes |
|------|---------|-------|
| **Frontend** | | |
| `AdminCortexOverviewPage.tsx` | **REPLACE** | → `OperatorOverviewPage.tsx` |
| `AdminCortexGraphPage.tsx` | **DELETE** | → Inspect lenses |
| `AdminCortexIdentityPage.tsx` | **DELETE** | → Inspect/identity |
| `AdminCortexIngestionPage.tsx` | **SIMPLIFY** | Connectors → Overview; runs → Queues |
| `AdminCortexCanonicalHealthPage.tsx` | **DELETE** | |
| `AdminCortexReconstructionPage.tsx` | **DELETE** | → Inspect/execution |
| `AdminCortexRetrievalPage.tsx` | **DELETE** | → Inspect/retrieval |
| `AdminCortexSynthesisPage.tsx` | **DELETE** | → Inspect/synthesis |
| `SemanticReadinessCard.tsx` | **DELETE** | |
| `OperatorPrimaryKpiCard.tsx` | **DELETE** | |
| `DeferralOmissionCard.tsx` | **DELETE** | doctrine → docs |
| `OperationalPhaseStrip.tsx` | **DELETE** | |
| `PhasePageShell.tsx` | **DELETE** | |
| `CanonicalSummaryPanels.tsx` | **DELETE** | |
| `fetchPipelineOverviewSlice.ts` | **DELETE** | |
| `usePipelineOverview.ts` | **DELETE** | |
| `graph/GraphTruthInspector.tsx` | **SIMPLIFY** | → snapshot summary + edge lookup |
| `graph/ExecutionThreadInspector.tsx` | **REPLACE** | placeholder → real thread search |
| `IdentityEntityCard.tsx` | **KEEP** | core evidence UI |
| `IdentityContinuityInspector.tsx` | **KEEP** | move under inspect/identity |
| `PipelineActions.tsx` | **SIMPLIFY** | → ActionPanel + `/operator/actions` |
| `AdminCortexSynthesisJobDetailPage.tsx` | **KEEP** | link from Inspect |
| `AdminCortexReasoningJobDetailPage.tsx` | **KEEP** | link from Inspect |
| **Backend routes** | | |
| `admin_cortex_pipeline.py` overview/* | **DELETE** | replace operator routes |
| `admin_cortex_pipeline.py` semantic-readiness | **DELETE** public | snapshot writer only |
| `admin_cortex_pipeline.py` graph-truth-inspector | **DELETE** | |
| `admin_cortex_pipeline.py` phases/*/summary* | **DELETE** | |
| `admin_cortex_pipeline.py` POST run | **SIMPLIFY** | → operator/actions |
| `admin_cortex_execution.py` | **SIMPLIFY** | merge POST into actions; GET into runtime |
| `admin_cortex_operational_runtime.py` | **DELETE** | ~100 dead routes |
| `admin_cortex_retrieval.py` catalogs | **DELETE** | keep lineage, query, health |
| `admin_cortex_synthesis.py` catalogs | **DELETE** | keep jobs/debugger |
| `admin.py` identity continuity routes | **KEEP** | wire to Inspect |
| **Backend builders** | | |
| `pipeline_admin_overview.py` | **DELETE** | replace `operator_admin_overview.py` |
| `continuity_overview_v1.py` | **SIMPLIFY** | snapshot writer only; delete HTTP path |
| `pipeline_admin_operator_kpi.py` | **DELETE** | |
| `pipeline_admin_semantic_readiness.py` | **MATERIALIZE** | writer task only |
| `semantic_readiness_v1.py` | **SIMPLIFY** | split: snapshot fields vs full audit script |
| `graph_truth_inspector_v1.py` | **DELETE** | edge lookup replaces |
| `pipeline_admin_graph_truth_inspector.py` | **DELETE** | |
| `pipeline_phase_views.py` summary paths | **DELETE** | keep explorer optional |
| `build_execution_inspect_v1` | **KEEP** | runtime backbone |
| `identity_continuity_inspector_v1.py` | **KEEP** | inspect backbone |
| `execution/admin_commands.py` | **KEEP** | actions |
| `pipeline_admin_run.py` | **SIMPLIFY** | fold into actions |
| `ingestion/admin_overview.py` | **KEEP** | lite connectors |
| `retrieval_artifact_lineage.py` | **KEEP** | inspect retrieval |
| `execution_island_registry.py` | **KEEP** | list registry; no sync on read |
| **Infra** | | |
| `cortex_admin_continuity_snapshot` table | **NEW** | materialize |
| Redis optional cache | **NEW** | phase R4 |

---

# Section 10 — Implementation Phases

## Phase R0 — Guardrails (2–3 days, no UX change) ✅ **Complete (2026-05-24)**

**Goal:** Stop production pain while refactor proceeds.

- ✅ Add `build_operator_overview_v1` behind flag `CORTEX_ADMIN_V2=0` (dark launch)
- ✅ Add request timing logs for existing bootstrap + semantic endpoints
- ✅ Feature flag frontend: `VITE_CORTEX_ADMIN_V2`
- ✅ Document deploy SHA in Settings footer (`GET /admin/build-info`, `VITE_GIT_SHA`, `VECTOR_GIT_SHA`)

**Deliverables:**

| Area | Path / note |
|------|-------------|
| Builder | `backend/src/vector/domains/cortex/pipeline/operator_admin_overview.py` |
| Route | `GET /admin/tenants/{id}/cortex/operator/overview` (404 when flag off) |
| Contracts | `backend/src/vector/contracts/operator_admin.py` |
| Timing | `backend/src/vector/api/http/admin_request_timing.py` on bootstrap + semantic-readiness |
| Build info | `GET /admin/build-info`, `vector/infrastructure/build_info.py` |
| Frontend | `frontend/src/admin/operator/*`, Settings `DeployInfoFooter` |
| Deploy | `VECTOR_GIT_SHA` + `VITE_GIT_SHA` in `.github/workflows/deploy.yml` |

**Operator value:** None visible except Settings deploy SHA footer. **Deletes:** nothing. **Rollback:** flag off.

---

## Phase R1 — Overview swap + delete slice fanout (1 week) ✅ **Complete (2026-05-24)**

**Highest immediate value.**

Backend:

- ✅ Implement `GET /operator/overview` (8-query cap) — extended with `runnable_connectors`, scheduler intervals
- ✅ Implement `cortex_admin_continuity_snapshot` table + writer task (basic)
- ✅ Mark bootstrap/phases/execution/ingestion routes `@deprecated`

Frontend:

- ✅ New `OperatorOverviewPage` behind flag (`AdminCortexOverviewGateway`)
- ✅ Remove layout prefetch bootstrap when v2 enabled
- ✅ Remove semantic-readiness fetch from overview (v2 path)
- ✅ Settings uses operator overview scheduler when v2 (no ingestion slice)

**Deliverables:**

| Area | Path / note |
|------|-------------|
| Snapshot table | migration `20260525_0094`, model `CortexAdminContinuitySnapshot` |
| Snapshot writer | `admin_continuity_snapshot.py`, Celery `refresh_admin_continuity_snapshot_task` + 10m sweep |
| Post-phase hook | `repository.complete_phase_v1` / `fail_phase_v1` → enqueue refresh (phases 03–08) |
| Overview UI | `frontend/src/admin/operator/OperatorOverviewPage.tsx` + sections |
| Gateway | `AdminCortexOverviewGateway.tsx` toggles legacy vs v2 |

**Deletes (v2 path):** frontend bootstrap path, semantic on overview, settings ingestion slice.

**Rollback:** `VITE_CORTEX_ADMIN_V2=0` + `CORTEX_ADMIN_V2=0` restores legacy Overview.

**Success metric:** Overview p95 < 500ms Fizzer; zero bootstrap 500s (validate in staging).

---

## Phase R2 — Runtime tab + unified actions (1 week) ✅ **Complete (2026-05-24)**

Backend:

- ✅ `GET /operator/runtime` via `build_operator_runtime_v1` (lean — no island registry scan; 15s cache; paginated transitions)
- ✅ `POST /operator/actions` via `execute_operator_action_v1` (pipeline run + execution POSTs + retrieval bootstrap)
- ✅ Operator actions audited via `CortexExecutionTransitionLog` (`operator_action:*` trigger)
- ✅ Legacy `pipeline/run` and execution POST routes marked `@deprecated`

Frontend:

- ✅ `OperatorRuntimePage` with lease truth, dual-lane facts, transition timeline, queue hints, full action panel
- ✅ `OperatorActionPanel` shared component — compact on Overview (safe actions), full on Runtime (destructive)
- ✅ Runtime tab in cortex nav when `VITE_CORTEX_ADMIN_V2=true`
- ✅ Overview compact actions call `POST /operator/actions` (not legacy `/pipeline/run`)

**Deliverables:**

| Area | Path / note |
|------|-------------|
| Runtime builder | `backend/src/vector/domains/cortex/pipeline/operator_admin_runtime.py` |
| Actions executor | `backend/src/vector/domains/cortex/pipeline/operator_admin_actions.py` |
| Routes | `GET /operator/runtime`, `POST /operator/actions` |
| Contracts | `OperatorRuntimeResponse`, `OperatorActionRequest/Response` in `operator_admin.py` |
| Frontend | `OperatorRuntimePage.tsx`, `OperatorActionPanel.tsx`, `AdminCortexRuntimeGateway.tsx` |
| Tests | `test_admin_cortex_operator_r2.py` |

**Deletes (v2 path):** `PipelineActions` flush on overview — moved to Runtime action panel.

**Operator value:** Can see **why blocked** via transition log without SQL; unified mutations via one endpoint.

---

## Phase R3 — Inspector hub + identity/graph (1.5 weeks) ✅ **Complete (2026-05-24)**

Backend:

- ✅ `GET /operator/snapshots/graph` — materialized graph summary reader (`build_operator_graph_snapshot_v1`)
- ✅ `GET /operator/inspect/edges` — on-demand edge provenance (`lookup_edge_provenance_v1`)
- ✅ `GET /operator/inspect/islands` — registry list without component scan
- ✅ Legacy `graph-truth-inspector` and `identity-continuity-inspector` marked `@deprecated`

Frontend:

- ✅ Inspector hub (zero fetch) + identity/graph/islands lenses under `/cortex/inspect`
- ✅ Identity search + entity card wired to existing continuity-inspector routes
- ✅ Graph snapshot prose + edge lookup on submit
- ✅ Legacy graph/identity tabs redirect to inspect when `VITE_CORTEX_ADMIN_V2=true`

**Deliverables:**

| Area | Path / note |
|------|-------------|
| Inspect builders | `backend/src/vector/domains/cortex/pipeline/operator_admin_inspect.py` |
| Routes | `/operator/snapshots/graph`, `/operator/inspect/edges`, `/operator/inspect/islands` |
| Contracts | `OperatorGraphSnapshotResponse`, `OperatorEdgeProvenanceResponse`, `OperatorIslandsListResponse` |
| Frontend | `frontend/src/admin/operator/inspect/*` |
| Gateways | `AdminCortexGraphGateway`, `AdminCortexIdentityGateway`, `AdminCortexInspectGateway` |
| Tests | `test_admin_cortex_operator_r3.py` |

**Deletes (v2 path):** graph-truth auto-fetch storm; graph/identity phase pages replaced by inspect lenses.

**Operator value:** See real entities and edge rules — core continuity evidence without SQL.

---

## Phase R4 — Queues tab + async components (1 week) ✅ **Complete (2026-05-24)**

Backend:

- ✅ `GET /operator/queues` with paginated failed synthesis, TCRE, deferrals, ingestion failed
- ✅ `POST /snapshots/graph/refresh` async Celery job (`refresh_graph_component_snapshot_task`)
- ✅ `cortex_admin_graph_component_snapshot` table + reader/writer

Frontend:

- ✅ `OperatorQueuesPage` + Queues tab in cortex nav
- ✅ Graph + Islands lenses with async component refresh + polling

**Deletes:** phase explorer as default UX (move to advanced/inspect optional).

---

## Phase R5 — Retrieval/synthesis inspect + lineage (1 week)

Backend:

- Wire lineage routes under `/operator/inspect/retrieval/lineage/...`
- Job search endpoint (paginated)

Frontend:

- Retrieval lens: epoch list + entry search + lineage chain UI
- Synthesis lens: job search → existing debugger
- Execution thread lens: walk/TCRE chain

**Deletes:** AdminCortexRetrievalPage, AdminCortexSynthesisPage, AdminCortexReconstructionPage.

**Operator value:** **PR → retrieval → synthesis** evidence chain.

---

## Phase R6 — Backend deletion (1 week)

- Remove bootstrap, monolith, slices, semantic public route, graph-truth-inspector
- Remove `pipeline_admin_overview.py`, operator KPI, continuity bundle HTTP path
- Hide/delete operational-runtime tenant routes
- Hide retrieval/synthesis catalog routes
- Remove legacy redirects after 30-day window

**Deletes the most complexity** (~150 route handlers).

**Rollback:** revert deploy; flags already off on old clients.

---

## Phase R7 — Frontend cleanup + contracts (3–4 days)

- Delete old pages, hooks, cards (Section 9 list)
- New `operator_admin.py` contracts only on wire
- Update integration tests: overview + runtime + one inspect path
- Remove `admin.py` contract fields for deleted surfaces

---

## Phase ordering rationale

```
R0 guardrails
 → R1 overview (immediate speed + truth)
 → R2 runtime (see blocked because + act)
 → R3 inspect identity/graph (see continuity evidence)
 → R4 queues + async graph (scale safety)
 → R5 retrieval/synthesis chains (intelligence loop visibility)
 → R6 backend delete (complexity cliff)
 → R7 frontend delete (maintainability)
```

**First operator-visible win:** R1 (fast overview with blocked-because + continuity facts).

**Biggest complexity deletion:** R6 (dead API removal).

---

## Rollback strategy

| Phase | Rollback |
|-------|----------|
| R1 | `VITE_CORTEX_ADMIN_V2=0` restores old Overview |
| R2 | Hide Runtime tab; old PipelineActions return |
| R3–R5 | Inspect lenses additive — disable routes |
| R6 | **Requires** R1–R5 stable 2 weeks; keep deprecated routes 1 release behind flag |
| R7 | Pure cleanup — git revert |

---

## Success criteria (definition of done)

1. Overview loads in <500ms p95 on Fizzer with **one** GET.
2. Operator can answer "why blocked" in <10s without SQL.
3. Operator can trace Slack handle → entity → edge rule → retrieval entry → synthesis claim.
4. Zero live connected-component scans on navigation.
5. Admin HTTP handlers reduced by >70%.
6. No "healthy" badge without link to terminal receipt or explicit "unknown".
7. Cortex admin codebase: operator frontend <30 files (down from ~45+).

---

**End of refactor plan.** R0–R4 complete; next step: R5 retrieval/synthesis inspect (enable flags in staging first).
