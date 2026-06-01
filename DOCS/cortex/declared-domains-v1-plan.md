# Cortex Declared Domains — V1 Plan (Final)

**Status:** Authoritative implementation & architecture plan  
**Date:** 2026-05-29 (architecture review revision)

**Scope:** Deterministic cross-tool rollups of **declared** work containers + momentum — V1 only

**Read first:** [`execution-scope-architecture.md`](execution-scope-architecture.md) — vocabulary and long-term boundaries

**Related:**

- [`graph-projection-v1-plan.md`](graph-projection-v1-plan.md) — upstream graph layer  
- [`identity-resolution-v1-plan.md`](identity-resolution-v1-plan.md) — participant resolution  
- [`scheduler-beat-tick-v1.md`](scheduler-beat-tick-v1.md) — orchestrator / pass runtime  
- [`operational-runtime/CORTEX_OPERATIONAL_RUNTIME_PHASES_v1.md`](operational-runtime/CORTEX_OPERATIONAL_RUNTIME_PHASES_v1.md)

---

## 0. Architecture review (pre-implementation)

Four areas validated before build. **No scope increase** — foundation corrections only.

### 0.1 Seed coverage — honest risk assessment

**The Linear-only framing in early drafts was too narrow.** Real tenants vary:

| Tenant pattern | Declared Domains V1 coverage | Risk |
|----------------|------------------------------|------|
| Linear with initiatives + projects | **High** — primary design target | Low |
| Linear projects/cycles only (no initiatives) | **Medium** — project seeds work | Low |
| Linear issues only (weak container use) | **Low** — few or no seeds | **Empty tab** |
| GitHub-primary (issues/PRs in repos) | **Low** — GH **repo** is a code container, not a declared domain | **Empty unless GH Project canonized** |
| Notion-primary (work in databases) | **Low in V1** — Notion DBs are **not** auto-seeds; see §7.1.1 | High if auto-seeded (garbage domains) |
| Slack-heavy, weak PM | **Very low** | **Empty** — acceptable; Emergent Domains is the future answer |
| Multi-tool (Linear + GH + Notion) | **High** when Linear seeds exist; Notion adds docs via graph only in V1 | Low |

**We cannot know exact percentages without tenant telemetry.** Engineering judgment:

- Initiatives are **not** universal even among Linear customers.
- **Projects** (or equivalent work containers) are more common than initiatives.
- A non-trivial slice of tenants will see **zero domains** in V1 — visible admin empty state (“no declared containers — Linear initiatives/projects required in V1”).

**Correct abstraction:** seeds are **explicit declared work containers**, not “Linear initiatives/projects.”

| V1 seed (via canon) | `declared_container_kind` |
|---------------------|---------------------------|
| Linear initiative | `initiative` |
| Linear project | `project` |
| Notion database | **Not V1** — requires deterministic qualification (§7.1.1) |
| GitHub Project / Milestone | **deferred** until canon maps them with a kind |
| Jira Epic / Project | **deferred** until connector exists |

**Do not** treat `entity_type=project` alone as a seed — it includes **GitHub repos** and **Notion databases** with different semantics. Seed eligibility is **`declared_container_kind` set at canon time**, not entity_type.

### 0.2 Canonical seed architecture (provider-agnostic)

**Do not** put `if linear` / `if jira` in `declared_domains/`.

**Do** classify seeds in **canon** at materialization time:

```
Connector mapper
    ↓
canon_entities row + attrs_json.declared_container_kind
    ↓
Declared Domains pass (reads kind only)
```

**Single registry:** `canon/declared_container_registry.py`

```python
# Conceptual — one file, connector knowledge lives here only
DECLARED_CONTAINER_SOURCES: dict[str, DeclaredContainerSource] = {
    "linear.initiative": DeclaredContainerSource(kind="initiative", ...),
    "linear.project": DeclaredContainerSource(kind="project", ...),
    # NOT unconditional:
    # "notion.database" — only via qualified path (§7.1.1), not blanket registry entry
    # future: "github.project": ..., "jira.epic": ...
}
```

On materialize, set `attrs_json.declared_container_kind` **only** when a registry rule or qualified path fires — never for all rows of a resource type by default.

**Declared Domains seed query:**

```text
canon_entities WHERE attrs_json.declared_container_kind IS NOT NULL
```

**Direct membership** also registry-driven — keyed by `declared_container_kind`, not connector:

| `declared_container_kind` | Work-item attr paths to match (examples) |
|---------------------------|------------------------------------------|
| `initiative` | `initiative_id` |
| `project` | `project_id` |
| `work_database` | `database_id`, parent database ref on rows — **only when seed qualified** |

Adding Jira later = **one registry entry + mapper** — no Declared Domains redesign.

**Notion warning:** most `notion.database` rows are **not** work containers (meeting notes, CRM, applicants, bugs-in-wrong-place, research, experiments). **Never** set `declared_container_kind` for every `notion.database` materialization.

**Not a new canon entity type in V1** — use `attrs_json` flags on existing materialized entities. Avoids schema churn; same pattern as graph reading canon refs.

**Rename in domain tables:** `seed_kind` → `declared_container_kind` (provider-agnostic).

### Future seed kinds (extension point)

**The Declared Domains pass must remain agnostic to seed type.** All provider-specific qualification lives in **canon** (`declared_container_registry.py` + materialize rules). The pass reads `declared_container_kind` and registry membership paths only.

**V1 / V1.1 seed kinds (shipped or planned):**

| `declared_container_kind` | Typical source |
|---------------------------|----------------|
| `initiative` | Linear initiative |
| `project` | Linear project |
| `work_database` | Pinned Notion database (qualified allowlist) |

**Future seed kinds (documentation only — not V1 scope):**

| Kind (illustrative) | Purpose |
|---------------------|---------|
| `roadmap_item` | Qualified Notion (or other) row representing a strategic bet / epic |
| `work_item_seed` | Qualified single work item as its own container seed |
| Other provider-qualified kinds | Jira epic, GitHub Project, etc. — one registry entry + mapper each |

Adding a seed kind = **registry entry + canon materialize qualification + membership attr paths**. No Declared Domains pass redesign.

**Invariant:** `declared_domains` rows are projections; `declared_container_kind` on canon entities are seeds. V1 uses 1:1 seed→domain; future kinds may change qualification rules but not the pass’s provider-agnostic shape.

### 0.3 Graph dependency — Level 0 / Level 1 (no starvation)

**Reject:** blocking Declared Domains until graph is caught up. That creates starvation during graph backlog, rebuild, or failure.

**Adopt two expansion levels:**

| Level | Name | Requires graph? | Membership source |
|-------|------|-----------------|-------------------|
| **0** | `direct` | **No** | Provider fields + registry attr paths on work items |
| **1** | `graph_expanded` | Yes (best-effort) | Level 0 + bounded BFS on `graph_relationships` |

**Pass behavior:**

1. Always materialize domains from seeds and **Level 0** memberships when canon seeds exist.
2. Attempt **Level 1** when graph rows exist for tenant; skip graph expansion if graph lane is behind — **do not block pass**.
3. Track `expansion_level` on `declared_domain_stats`: `direct` | `partial_graph` | `graph_current`.
4. When graph catches up / rebuild completes, dirty enqueue → Level 1 fills in on next pass.

**Planning:** Declared Domain passes are scheduled on **own dirty queue**, independent of graph caught-up gating. Admin may show advisory “graph behind — cross-tool expansion incomplete.”

**During graph rebuild:** Level 0 stable; Level 1 memberships from missing/stale edges are **not deleted** until re-walk proves unreachable (supersede on pass, not on graph delete).

### 0.4 Momentum — fix the tiny-initiative problem

Raw `momentum_pct` is **misleading** for cross-domain ranking (1→3 = +200% beats 500→600).

**V1 metrics (always separate, never blended):**

| Metric | Field | Meaning |
|--------|-------|---------|
| **Mass** | `mass_total` | How big is this domain (artifact count) |
| **Activity** | `events_7d` | How much happened this week |
| **Activity delta** | `activity_delta_7d` | `events_7d - events_prior_7d` (absolute) |
| **Momentum %** | `momentum_pct` | Only meaningful at scale — **detail view / optional column** |

**Ranking rules (no single “hotness” score):**

| User intent | Sort by | Filter |
|-------------|---------|--------|
| Biggest domains | `mass_total` DESC | — |
| Most active this week | `events_7d` DESC | — |
| Largest increase in activity | `activity_delta_7d` DESC | `events_7d >= MIN` AND `events_prior_7d >= MIN_BASELINE` |
| Cooling | `activity_delta_7d` ASC | `events_prior_7d >= MIN_BASELINE` |

Defaults: `MIN = 3`, `MIN_BASELINE = 5` for delta/momentum displays.

**Show `momentum_pct` only when** `events_prior_7d >= MIN_BASELINE` — otherwise show “—” or “low baseline” in UI.

**Explicitly reject:** single hotness index, blended health scores, momentum-only default sort.

---

## 1. What this is

**Declared Domains** are a deterministic projection layer — architecturally identical to canon, identity, and graph.

> For each **declared work container** (canon entity with `declared_container_kind`), materialize cross-tool artifacts, participants, activity, and momentum.

Seeds are **provider-agnostic** — classified in `canon/declared_container_registry.py`, not in Declared Domains logic.

### V1 answers

| Question | Answer |
|----------|--------|
| What declared domains exist? | One domain per eligible canon seed |
| What belongs to each domain? | Deterministic membership via seed + graph expansion |
| Who is involved? | Identity-resolved participants from member artifacts |
| Is activity increasing or decreasing? | Activity delta (absolute) + optional momentum % when baseline sufficient |

### V1 does not answer

- What undeclared concerns exist → **Emergent Domains** (future)
- What is the company working on overall → execution scope union (future)
- Is this domain at risk → **Execution Intelligence** (future)

### Honest positioning

Cortex adds **cross-tool aggregation**, **participant rollup**, and **activity trends** on containers the org already declared in their PM tools. **V1 seeds: Linear initiatives and projects only.** When no qualified seeds exist in canon, the tab is **empty by design** — not a failure.

### Semantic caveat

**A Declared Domain V1 must not be interpreted as proof that the underlying seed represents the correct execution-scope granularity for every tenant.**

V1 materializes the **declared container boundary** the canon registry qualified — one projection row per seed. It does **not** assert that every seed is a “domain” in the sense an EM would use in conversation.

| Seed | Typical alignment with human execution scope |
|------|-----------------------------------------------|
| Linear project | **Often close** — bounded body of work with scoped issues |
| Linear initiative | **Often close** — strategic theme spanning projects |
| Pinned Notion roadmap database (`work_database`) | **Often a portfolio container** — rows inside may be closer to “domains” than the database itself |

**Examples:**

- **Linear Project “Billing Rewrite”** → declared domain rollup is usually meaningful at project granularity.
- **Pinned Notion database “Global Roadmap”** → declared domain rollup is a **backlog/portfolio scope**; individual rows (JWT Authentication, Android Hiring, …) are **members**, not separate declared domains in V1.

Future versions may add **finer-grained seed kinds** (e.g. qualified row-level seeds) via the canon registry — without changing the Declared Domains pass architecture. See §Future seed kinds (extension point).

---

## 2. Philosophy

Declared Domains must feel like graph and identity:

| Property | Requirement |
|----------|-------------|
| Deterministic | Same canon + graph + extractor version → same memberships |
| Replayable | Bump `extractor_version`; full tenant rebuild |
| Explainable | Every membership row has `extractor_rule` + evidence |
| Incremental | Dirty queue; no full-tenant nightly recompute |
| Operationally boring | One pass type, one module, shared runtime |

**Not:** semantic clustering, topic discovery, AI topics, execution intelligence, ontology.

---

## 3. Stack position

```
Ingestion
    ↓
Canon  (+ declared_container_kind on seed entities)
    ↓
Identity
    ↓
Graph ──────────────┐
    ↓               │ (Level 1 expansion; optional, non-blocking)
Declared Domains  ←─┘
```

Declared Domains is a **separate projection layer**. Level 0 (direct) runs without graph. Level 1 (graph expansion) is additive.

Emergent Domains and Execution Intelligence remain future layers below.

---

## 4. Runtime integration (no snowflake architecture)

Declared Domains uses the **same runtime model** as canon, identity, and graph. No new worker fleet, Beat entry, or orchestration framework.

### 4.1 Pass type

| Constant | Value |
|----------|-------|
| `DECLARED_DOMAIN_PASS` | `"declared_domain_pass"` |

Registered in `runtime/pass_types.py` alongside `canon_pass`, `identity_pass`, `graph_projection_pass`.

### 4.2 Authoritative queue

**`cortex_passes`** — same claim/lease/retry semantics as other lanes (`runtime/queue.py`, `runtime/claim.py`, `runtime/execute.py`).

### 4.3 Pass execution

```
runtime/execute.py
  elif row.pass_type == DECLARED_DOMAIN_PASS:
      execute_declared_domain_pass_for_tenant(...)
```

Implementation: `domains/cortex/declared_domains/materialize.py`

### 4.4 Planning (orchestrator tick)

`runtime/plan.py` adds a block mirroring graph:

```text
if declared_domain_scheduler_enabled and not lane_paused("declared_domains"):
  for tenant in iter_tenants_with_declared_domain_backlog():
    if should_skip_scheduled_declared_domain_pass(interval):
      skip
    upsert_pending_pass_v1(tenant, DECLARED_DOMAIN_PASS, source_trigger="scheduled")
```

**Backlog signal:** unprocessed rows in `declared_domain_dirty_queue` OR canon seed entities with `declared_container_kind` needing (re)processing.

**Graph dependency:** **Do not gate** pass planning on graph caught-up. Graph backlog may delay Level 1 expansion only; Level 0 always proceeds. Admin surfaces `expansion_level` per domain.

**Default interval:** `CORTEX_DECLARED_DOMAIN_SCHEDULER_INTERVAL_SECONDS` = 300 (match canon/identity/graph).

### 4.5 Tick behavior

| Event | Behavior |
|-------|----------|
| Orchestrator tick (120s default) | `plan_cortex_passes_v1` may enqueue `declared_domain_pass` |
| Poll worker | Claims `cortex_passes` row, runs one pass batch |
| Pass iteration | Drain dirty queue batch → expand memberships → recompute stats → audit |

One scheduled pass = **one batch** (like identity/graph), not full drain unless admin `drain: true`.

### 4.6 Dirty queue

**Table:** `declared_domain_dirty_queue` (mirror `graph_dirty_queue`)

| Column | Purpose |
|--------|---------|
| `tenant_id` | Scope |
| `canon_entity_id` | Seed or member entity to reprocess |
| `reason` | `seed_materialized`, `member_materialized`, `graph_updated`, `extractor_bump`, `rebuild` |
| `enqueued_at`, `processed_at`, `attempts`, `last_error` | Ops |

**Enqueue hooks (thin, one line each):**

- `canon/materialize.py` — when registry marks resource as declared container → set `declared_container_kind` + enqueue seed
- `canon/materialize.py` — when scoped member types materialized → `enqueue_declared_domain_entity` (optional: only if attrs link to known seed)
- `graph/materialize.py` — after edge upsert affecting expansion → enqueue source entity (same pattern as graph dirty)

No extraction logic in canon/graph modules — enqueue only.

### 4.7 Pass run audit

**Table:** `declared_domain_pass_runs` (mirror `graph_pass_runs`)

| Field | Example |
|-------|---------|
| `status` | RUNNING / COMPLETED / FAILED |
| `source_trigger` | scheduled / admin / rebuild |
| `stats_json` | `{domains_touched, memberships_upserted, memberships_superseded, stats_recomputed, dirty_processed, errors}` |

Dual audit: `cortex_passes` (queue) + `declared_domain_pass_runs` (domain stats).

### 4.8 Replay & rebuild

| Operation | Mechanism |
|-----------|-----------|
| **Extractor bump** | Increment `declared_domains/extractor_version.py`; enqueue all seeds with `extractor_bump` |
| **Tenant rebuild** | Admin action: supersede all memberships, re-walk from seeds, recompute stats |
| **Full replay** | Delete `declared_domain_*` for tenant; re-run passes from canon seeds |

Memberships use `status: active | superseded` — never hard delete (matches graph).

### 4.9 Retry / recovery

Reuse `cortex_passes` `attempt_count`, `max_attempts`, stale `RUNNING` abandonment via `declared_domains/pass_run_ops.py` (mirror `graph/pass_run_ops.py`).

### 4.10 Lane pause & staleness

- `read_lane_paused_flag(settings, "declared_domains")`
- `runtime/lane_scheduler_status.py` — stale badge when tenant needs work, no active pass, no recent completion
- `scheduler-beat-tick-v1.md` — document new lane in table

**Explicit rejection:** Dedicated Celery queue, dedicated ECS service, dedicated Beat entry, custom scheduler loop.

---

## 5. Module isolation

```
backend/src/vector/domains/cortex/declared_domains/
├── __init__.py
├── materialize.py       # pass execution
├── enqueue.py           # dirty queue writes
├── expand.py            # deterministic seed → membership expansion
├── stats.py             # momentum + rollups
├── scheduler.py         # iter_tenants_with_declared_domain_backlog
├── scheduler_dedup.py   # should_skip_scheduled_declared_domain_pass
├── pass_run_ops.py      # abandon stuck RUNNING
├── admin.py             # read APIs (no HTTP here)
├── extractor_version.py
├── declared_container_registry.py   # READ-ONLY re-export of canon registry for domain module
└── expansion_rules.py   # Level 0 attr paths by kind; Level 1 graph edges

canon/ (seed classification — connector knowledge lives here only)
├── declared_container_registry.py
└── mappers/*

infrastructure/db/models/
├── declared_domain.py
├── declared_domain_membership.py
├── declared_domain_stats.py
├── declared_domain_dirty_queue.py
└── declared_domain_pass_run.py

frontend/src/admin/cortex/
├── AdminCortexDeclaredDomainsPage.tsx
├── DeclaredDomainsStateTab.tsx
├── DeclaredDomainsRunsTab.tsx
├── DeclaredDomainsDataTab.tsx
├── DeclaredDomainDetailPanel.tsx
└── useDeclaredDomainsReadiness.ts
```

### What must NOT live in `declared_domains/`

| Concern | Location |
|---------|----------|
| Pass claim/lease | `runtime/` |
| Orchestrator | `app/tasks/cortex_runtime.py` |
| HTTP routes | `api/http/routes/admin.py` (thin) |
| Graph extraction | `graph/` |
| Identity matching | `identity/` |

---

## 6. Data model

### Design principle

**Store projections, not copies.** Membership rows reference `canon_entity_id` and optional `graph_relationship_id` / `evidence_ref` — not artifact payloads.

### Table 1: `declared_domains`

**Purpose:** Stable identity for one declared seed.  
**Ownership:** `declared_domains` module.  
**Rebuild:** Upsert from canon seeds; `id` stable per `(tenant_id, seed_canon_entity_id)`.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | Stable domain id |
| `tenant_id` | UUID | |
| `display_name` | string | From seed `attrs_json` / title at materialization |
| `declared_container_kind` | string | Provider-agnostic: `initiative`, `project`, `work_database`, … |
| `seed_canon_entity_id` | UUID FK → `canon_entities` | **Unique** per tenant |
| `seed_connector` | string | Denorm from canon for admin display |
| `seed_resource_type` | string | Denorm e.g. `linear.initiative` — audit only |
| `extractor_version` | int | Last version that touched domain |
| `first_observed_at` | timestamptz | |
| `last_activity_at` | timestamptz | Denormalized from stats refresh |
| `created_at`, `updated_at` | timestamptz | |

**Lifecycle:** Created when seed entity first seen; persists while seed exists. No merge/split in V1.

### Table 2: `declared_domain_memberships`

**Purpose:** Artifact ∈ domain with evidence.  
**Ownership:** `declared_domains` module.  
**Rebuild:** Delete/supersede all for tenant; re-expand from seeds.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID | |
| `declared_domain_id` | UUID FK | |
| `canon_entity_id` | UUID FK | Member artifact |
| `extractor_version` | int | |
| `extractor_rule` | string | e.g. `direct.container_ref`, `graph.closes` |
| `expansion_level` | string | `direct` or `graph` — which phase produced this row |
| `evidence_kind` | string | `provider_field`, `graph_edge`, `seed_entity` |
| `evidence_ref` | string | JSON path, edge id, or seed id |
| `seed_distance` | smallint | 0 = seed itself; 1–2 = expansion hops |
| `observed_at` | timestamptz | From source artifact |
| `status` | string | `active`, `superseded` |
| `superseded_at` | timestamptz nullable | |

**Unique active:** `(tenant_id, declared_domain_id, canon_entity_id, extractor_rule)` WHERE `status = active`.

### Table 3: `declared_domain_stats`

**Purpose:** Denormalized rollup cache for list UI and MCP.  
**Ownership:** `declared_domains` module.  
**Rebuild:** Recompute from active memberships + canon timestamps every pass. Safe to drop.

| Column | Type | Notes |
|--------|------|-------|
| `declared_domain_id` | UUID PK/FK | One row per domain |
| `tenant_id` | UUID | |
| `artifact_counts_json` | JSONB | `{work_item: 12, pull_request: 5, message: 40, …}` |
| `participant_count` | int | Distinct identities |
| `participant_identity_ids` | JSONB | Optional cap top-N for detail view |
| `events_7d` | int | Activity this window |
| `events_prior_7d` | int | Prior window |
| `activity_delta_7d` | int | `events_7d - events_prior_7d` (primary “growing” sort) |
| `momentum_pct` | numeric nullable | % change; **null** when `events_prior_7d < MIN_BASELINE` |
| `mass_total` | int | Sum of artifact counts (for sort) |
| `expansion_level` | string | `direct` \| `partial_graph` \| `graph_current` |
| `computed_at` | timestamptz | |

**Why separate from `declared_domains`:** Large membership sets; stats recompute locks one row without touching domain identity.

### Tables explicitly rejected for V1

| Rejected | Why |
|----------|-----|
| `declared_domain_participants` | Derive from memberships + identity at read or stats refresh |
| `declared_domain_momentum_history` | Use `declared_domain_pass_runs.stats_json` + admin drilldown; no time-series DB |
| `declared_domain_lifecycle_events` | Deferred |
| Copy of graph edges | Reference graph at expansion time only |

### Infrastructure tables (standard pattern)

- `declared_domain_dirty_queue`
- `declared_domain_pass_runs`
- Uses existing `cortex_passes`

---

## 7. Membership strategy

### 7.1 Seed sources — canon `declared_container_registry`

Seeds are **not** selected by `entity_type` alone (`project` includes GH repos and Notion DBs).

| Registry key (`resource_type`) | `declared_container_kind` | V1 ship |
|-------------------------------|---------------------------|---------|
| `linear.initiative` | `initiative` | **Yes** |
| `linear.project` | `project` | **Yes** |
| `notion.database` | `work_database` | **V1.1** — pinned allowlist only; §7.1.1 |
| `github.repository` | — | **No** — code container, not declared domain |
| `github.project` (future) | `program_board` | Defer until canon maps |
| `jira.epic` (future) | `epic` | Defer until connector |

Mappers set `attrs_json.declared_container_kind` and `declared_container_external_id` **only** when a seed rule qualifies.

#### 7.1.1 Notion databases — conservative seed policy

**Default: `notion.database` → NOT a declared domain seed.**

Not every Notion database is a project, initiative, or roadmap. Typical workspaces also have databases for meeting notes, customers, applicants, bugs, research, experiments, etc. Auto-tagging all `notion.database` canon rows as `work_database` would produce **garbage domains**.

**V1 rule:** Declared Domains **does not** auto-consume every `notion.database`. **V1.1 (shipped):** operator pins databases per Notion connection (`work_container_pins`); see [`notion-declared-domains-v1-plan.md`](notion-declared-domains-v1-plan.md).

**Future Notion qualification (all must be deterministic; no AI):**

| Qualification path | When acceptable |
|--------------------|-----------------|
| **Operator allowlist** | Tenant admin explicitly pins database id(s) as declared containers |
| **Connector config** | Per-connection list of database ids flagged `is_work_container` at setup |
| **Structural gate** | Mapper sets kind only if raw database metadata passes **documented** rules (e.g. required property schema template id) — spec before implement |

**Forbidden:**

- `entity_type=project` + `connector=notion` → automatic seed
- Title/name heuristics (“Roadmap”, “Projects”) as sole signal
- Row count or activity volume as seed signal

Until a qualification path ships, Notion rows remain canon `project` entities for materialization/graph only — **no** `declared_container_kind`.

### 7.2 Level 0 — Direct membership (`expansion_level=direct`)

Does **not** require graph.

- Work items / rows where container ref attrs match seed external id (paths from registry by `declared_container_kind`)
- Seed entity itself when artifact-bearing

### 7.3 Level 1 — Graph expansion (`expansion_level=graph`)

**Additive.** Skipped when graph lane behind; pass still completes Level 0.

Bounded BFS from Level 0 members (max depth 2):

| `extractor_rule` | Graph edge |
|------------------|------------|
| `graph.closes` | `closes` |
| `graph.references` | `references` |
| `graph.mentions` | `mentions` |
| `graph.comments_on` | `comments_on` |
| `graph.replies_to` | `replies_to` |
| `graph.parent_of` | `parent_of` |

### 7.4 Stop conditions

| Rule | Value |
|------|-------|
| Max BFS depth | **2** hops from direct members |
| Allowed entity types | `work_item`, `pull_request`, `message`, `conversation`, `document`, `commit`, `deployment` — not `actor` as membership (actors via participants) |
| Edge confidence | Only `active` graph relationships with `confidence` in `certain`/`high` |
| No semantic edges | Never expand via embedding, label similarity, or shared assignee alone |

### 7.5 Overlap

Work item in two seeds → **two domains**, both get membership. Overlap is visible; no merge in V1.

### 7.6 Rebuild semantics

On pass for dirty entity:

1. Load affected domains (seeds + domains containing entity)
2. Re-run expansion from seed set for those domains
3. Supersede memberships no longer reachable
4. Upsert new memberships
5. Recompute stats for touched domains

---

## 8. Activity metrics (not “hotness”)

### Three separate concepts — never blend

| Concept | Field | User question |
|---------|-------|---------------|
| **Mass** | `mass_total` | "How big is this domain?" |
| **Activity** | `events_7d` | "How much happened this week?" |
| **Activity delta** | `activity_delta_7d` | "How much more/less than last week?" |
| **Momentum %** | `momentum_pct` | Optional; only when prior baseline sufficient |

### Computation

```text
events_7d           = distinct member artifacts with activity in (now-7d, now]
events_prior_7d     = distinct member artifacts with activity in (now-14d, now-7d]
activity_delta_7d   = events_7d - events_prior_7d
momentum_pct        = activity_delta_7d / max(events_prior_7d, 1) * 100
                      OR NULL when events_prior_7d < MIN_BASELINE (default 5)
```

Activity timestamp: single rule in `stats.py` — prefer `observed_at` on membership row (sourced from canon `materialized_at` or latest source revision).

### Ranking (API / admin — no default “hotness”)

| Endpoint / sort | Field |
|-----------------|-------|
| `sort=mass` | `mass_total` DESC |
| `sort=activity` | `events_7d` DESC |
| `sort=growing` | `activity_delta_7d` DESC, filter `events_7d >= 3` |
| `sort=shrinking` | `activity_delta_7d` ASC, filter `events_prior_7d >= 5` |

**Reject:** default combined hotness rank, momentum-only leaderboards, blended scores.

### Momentum "history" in admin

No history table. **Runs tab** shows `stats_json` from past passes; **detail view** shows current stats + last computed_at. V1.5 may add snapshots if needed.

---

## 9. Admin / Cortex UI

New top-level tab: **Declared Domains** — same layout pattern as Links (graph).

Route: `/admin/tenants/:tenantId/cortex/declared-domains`

Sub-tabs: **Overall state** | **Runs** | **Data** (identical nav pattern to `AdminCortexGraphPage.tsx`).

### 9.1 Overview (State tab)

| Metric | Source |
|--------|--------|
| Total domains | `count(declared_domains)` |
| Active domains | `events_7d > 0` |
| Dormant domains | `events_7d = 0` and stale |
| Fastest growing | top 5 by `activity_delta_7d` (with baseline filters) |
| Largest | top 5 by `mass_total` |
| Most active | top 5 by `events_7d` |
| Empty state | `total domains = 0` — explain seed coverage (no declared containers in canon) |
| Dirty queue pending | `declared_domain_dirty_queue` unprocessed |
| Caught up | dirty = 0 and no pending pass |
| Graph expansion | advisory: `expansion_level` counts (`direct` vs `graph_current`) |

### 9.2 List view (Data tab)

Searchable, sortable table.

| Column | Notes |
|--------|-------|
| Name | `display_name` |
| Seed | `declared_container_kind` + connector + link to canon seed |
| Mass | `mass_total` |
| Activity (7d) | `events_7d` |
| Δ Activity | `activity_delta_7d` |
| Momentum % | `momentum_pct` or "—" if low baseline |
| Expansion | `expansion_level` badge |
| Participants | `participant_count` |
| Last activity | `last_activity_at` |

Filters: seed kind, dormant/active, min mass, min momentum.

### 9.3 Domain detail

Panel or route `/declared-domains/:domainId`:

| Section | Content |
|---------|---------|
| Metadata | seed, extractor version, first/last observed |
| Stats | mass breakdown by modality, activity, momentum |
| Participants | identity display names (top N) |
| Artifacts | paginated memberships with `extractor_rule`, evidence link |
| Seed | link to canon seed drilldown |

Everything inspectable — click membership → show why (rule + evidence ref).

### 9.4 Operations (Runs tab)

Match graph runs tab:

- Pass run history (`declared_domain_pass_runs`)
- Status, duration, stats_json
- Manual pass trigger (confirmation phrase e.g. `RUN DECLARED DOMAIN PASS`)
- Rebuild tenant button (confirmation phrase)
- Dirty queue depth + oldest unprocessed

### 9.5 Stale badge

Cortex nav tab shows stale indicator when `lane_scheduler_status` reports declared-domains lane stale (same component pattern as canon/identity).

---

## 10. Observability

| Surface | Content |
|---------|---------|
| `GET .../declared-domains/readiness` | extractor version, dirty count, caught up, graph/canon dependency flags, scheduler |
| `GET .../declared-domains/pass-runs` | audit history |
| `GET .../operations` | include `declared_domain_planned/skipped` in orchestrator plan stats |
| Pass `stats_json` | domains touched, memberships upserted/superseded, errors |
| Logs | single logger prefix `declared_domains` per pass run id |

Debug flow: membership row → `extractor_rule` + `evidence_ref` → graph edge or canon field → raw via canon entity drilldown.

---

## 11. MCP / read API (V1)

| Endpoint | Returns |
|----------|---------|
| `GET /declared-domains` | List; `sort=mass|activity|growing|shrinking|name` |
| `GET /declared-domains/{id}` | Domain + stats + participants |
| `GET /declared-domains/{id}/artifacts` | Paginated memberships |
| `GET /declared-domains/growing` | Top N by `activity_delta_7d` (filtered) |
| `GET /declared-domains/shrinking` | Bottom N by `activity_delta_7d` (filtered) |

---

## 12. Explicitly deferred (do not implement in V1)

| Deferred | Why |
|----------|-----|
| Emergent Domains | Different trust model; hybrid |
| Execution Intelligence | Interpretation layer |
| Embeddings / clustering | Semantic discovery |
| LLM topic naming / summarization | Synthesis |
| Merge / split domains | No measured pain |
| Taxonomy / ontology | Not Cortex |
| Semantic search | Retrieval layer |
| Knowledge graph edges for domain | Separate projection tables only |
| Risk / delivery / forecasting | Intelligence |
| Lifecycle FSM (nascent/peaking/dormant) | `last_activity_at` + momentum enough |
| Membership confidence bands | Binary membership in V1 |
| Candidate → promotion pipeline | Emergent layer |
| Notion database auto-seeding | §7.1.1 — qualification required |
| Single hotness ranking | Use separate sorts |
| Momentum history table | Pass run audit sufficient |
| `belongs_to_domain` graph edge type | Pollutes graph |
| Dedicated worker / queue / Beat | Violates runtime philosophy |
| Cross-tenant domain templates | — |
| Label/cycle/team as seeds | Organizational, not declared container |
| Shared-assignee expansion | Fuzzy; not explicit |
| Synthesis / retrieval integration | Domains must prove useful first |

**Rule:** If it interprets meaning beyond explicit declared container + graph rule, defer.

---

## 13. Rollout plan

### Phase 0 — Schema & registry

- Alembic: 5 tables + indexes
- `canon/declared_container_registry.py` + mapper hooks for **Linear initiative/project only**
- `declared_domains/` module skeleton
- Pass type registered

### Phase 1 — Level 0 domains

- Upsert domains from canon seeds (`declared_container_kind` set)
- Direct membership via container ref attrs
- Stats: mass + activity (no graph)

### Phase 2 — Level 1 graph expansion

- BFS expanders; `expansion_level` on stats
- Non-blocking when graph behind
- Enqueue hooks from graph

### Phase 3 — Activity delta metrics

- `activity_delta_7d`, conditional `momentum_pct`
- Three explicit sort paths

### Phase 4 — Runtime

- `plan.py` + scheduler + dedup + lane stale
- Pass run audit + abandon stuck RUNNING

### Phase 5 — Admin UI

- Tab + State / Runs / Data
- Detail panel with evidence inspectability

### Phase 6 — MCP read APIs

- List, detail, growing/shrinking

### Phase 7 — Prod validation

- Tenant with Linear initiatives
- Verify cross-tool expansion (Slack → issue → initiative)
- EM review: is rollup trustworthy?

**Gate before Emergent Domains:** Declared Domains used in prod + documented coverage gap.

---

## 14. Settings (new)

| Setting | Default | Purpose |
|---------|---------|---------|
| `CORTEX_DECLARED_DOMAIN_SCHEDULER_ENABLED` | true | Lane on/off |
| `CORTEX_DECLARED_DOMAIN_SCHEDULER_INTERVAL_SECONDS` | 300 | Dedup interval |
| `CORTEX_DECLARED_DOMAIN_BATCH_ENTITY_LIMIT` | 500 | Dirty queue batch |
| `CORTEX_DECLARED_DOMAIN_EXPANSION_MAX_DEPTH` | 2 | BFS cap |
| `CORTEX_DECLARED_DOMAIN_MOMENTUM_MIN_BASELINE` | 5 | Min prior events to show momentum % |
| `CORTEX_DECLARED_DOMAIN_ACTIVITY_MIN_EVENTS` | 3 | Min current events for growing sort |

---

## 15. Open questions

1. **Notion (post-V1):** which qualification path first — operator allowlist vs connector config vs structural gate?
2. Identity participant cap in stats JSON: count-only in V1; detail view queries live.
3. Empty-state copy in admin: per-connector hints when Linear connected but no initiatives/projects materialized.

---

## Summary

Declared Domains V1 is **graph-shaped**: dirty queue, pass on `cortex_passes`, domain module, pass run audit, admin State/Runs/Data, deterministic expansion, no AI.

It is the **Declared** branch under **Execution Scope** — not the whole scope, not intelligence.

```
Execution Scope
├── Declared Domains (V1)     ← this plan
└── Emergent Domains (future)

Execution Intelligence (future) → consumes both
```
