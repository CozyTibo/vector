# Notion Declared Domains — V1.1 Plan

**Status:** Shipped (V1.1)  
**Date:** 2026-05-29  
**Parent:** [`declared-domains-v1-plan.md`](declared-domains-v1-plan.md) · [`execution-scope-architecture.md`](execution-scope-architecture.md)

**Problem:** Tenants like **Fizzer** (Notion-only, no Linear) see **0 declared domains** today. That is correct for V1, but unacceptable as a long-term product gap for Notion-primary companies.

**Goal:** Let Notion-primary workspaces declare **which databases are work containers** and get the same deterministic rollups (mass, activity, momentum, graph expansion) as Linear initiative/project seeds — **without** auto-seeding every `notion.database`.

---

## 1. Principles (unchanged from parent plan)

| Rule | Rationale |
|------|-----------|
| **No auto-seed all Notion databases** | Most workspaces mix roadmaps with CRM, notes, hiring, experiments |
| **Qualification is deterministic** | Operator/config/structural gate only — no AI, no title heuristics alone |
| **Canon owns seed classification** | `declared_container_kind` set at materialize time in `declared_container_registry.py` |
| **Declared Domains stays provider-agnostic** | Reads `declared_container_kind` + registry attr paths only |
| **`entity_type=project` ≠ seed** | Notion DB and GH repo both map to `project`; seed = explicit kind |

---

## 2. Recommended qualification path: **connection allowlist** (V1.1)

Ship **one** path first. Defer structural gates until we have real customer schema templates.

### 2.1 Connection-level work database allowlist

Per Notion `TenantConnection`, tenant admin pins **explicit database IDs** that are declared work containers.

```text
notion_connection_details
  └── work_container_database_ids: text[]   # Notion database UUIDs
```

**Materialize rule** (in canon, not declared_domains):

```text
IF resource_type = notion.database
AND external_id IN connection.work_container_database_ids
THEN attrs.declared_container_kind = work_database
     attrs.declared_container_external_id = external_id
ELSE do not set declared_container_kind
```

**Why this path first**

| Criterion | Allowlist | Auto all DBs | Title heuristics |
|-----------|-----------|--------------|------------------|
| False positives | Low (human pins) | Very high | High |
| Notion-only tenants | Works day one | Broken | Broken |
| Implementation cost | Small | Tiny but wrong | Medium, still wrong |
| Fizzer unblock | Yes — admin pins 2–5 real DBs | No | No |

### 2.2 Deferred paths (V1.2+)

| Path | When |
|------|------|
| **Structural gate** | When we document 1–2 Notion “work DB” property templates (Status + Assignee + Due, etc.) and can match deterministically |
| **Per-row work_item canon type** | If we later map `notion.database_row` → `work_item` instead of `document` for allowlisted DBs only |
| **Workspace-wide default** | Never — always explicit pin |

---

## 3. Canon changes

### 3.1 Registry extension

`canon/declared_container_registry.py`:

```python
CONTAINER_MEMBERSHIP_ATTR_PATHS = {
    "initiative": ("initiative_id",),
    "project": ("project_id",),
    "work_database": ("database_id",),  # new
}
```

**Do not** add unconditional `"notion.database": DeclaredContainerSource(...)` to `DECLARED_CONTAINER_SOURCES`. Qualification calls a separate function:

```python
def declared_container_kind_for_materialize(
    *,
    resource_type: str,
    connection_id: UUID,
    external_id: str,
    connection_work_db_allowlist: frozenset[str] | None,
) -> str | None:
    if resource_type == "linear.initiative":
        return "initiative"
    if resource_type == "linear.project":
        return "project"
    if resource_type == "notion.database" and connection_work_db_allowlist:
        if external_id in connection_work_db_allowlist:
            return "work_database"
    return None
```

### 3.2 Notion mapper — `database_id` on rows

Level 0 membership requires rows to carry the container ref.

**Today:** `notion.database_row` → `document`; parent ref exists but **`database_id` not in attrs**.

**Change:** When parent type is `database_id`, set:

```python
attrs["database_id"] = parent_database_id
```

Also set on `notion.page` when parent is a database (if ingested).

### 3.3 Mass weights

`declared_domains/mass.py`:

```python
"document": 5,  # already exists — database rows count toward domain mass
```

No new entity type required for V1.1 if rows stay `document`.

### 3.4 Re-materialize on allowlist change

When admin adds/removes a database from the allowlist:

1. Persist new allowlist on `notion_connection_details`
2. Enqueue **canon dirty** or **declared-domain rebuild** for affected database canon entities + all rows in those DBs
3. Canon re-materialize re-stamps or clears `declared_container_kind`
4. Declared domain pass supersedes stale memberships

---

## 4. Declared Domains module changes

**Minimal** — mostly already generic.

| Area | Change |
|------|--------|
| `sync_domains_from_seeds` | No change — already queries `declared_container_kind` |
| `expand.py` Level 0 | Picks up `work_database` via registry `database_id` path |
| `expand.py` Level 1 | Unchanged — graph BFS from row/page members |
| `stats.py` | Unchanged |
| `admin.py` readiness | Empty state copy: “Pin Notion work databases in Integrations” |
| Seed display | `declared_container_kind=work_database`, `seed_connector=notion` |

### 4.1 Membership model for Notion

| Member | Level 0 rule | Notes |
|--------|--------------|-------|
| `notion.database_row` in pinned DB | `direct.container_ref` via `database_id` | Primary |
| Pinned database seed entity | Optional `direct.seed_entity` if we count DB as artifact | Low mass |
| Linked `notion.page` | Level 1 via `parent_of` / `references` | After graph |
| Slack/GitHub artifacts | Level 1 graph | Same as Linear domains |

---

## 5. Admin & operator UX

### 5.1 Integrations → Notion → Work containers

New section on Notion connection (or Cortex Declared Domains empty state CTA):

1. **List canon databases** for tenant (`entity_type=project`, `connector=notion`) with title, external id, row count (from stats or canon).
2. **Pin / unpin** toggle per database → updates `work_container_database_ids`.
3. **Confirmation** on first pin: “Only pin databases used as project/roadmap backlogs.”
4. **Save** → triggers backfill job (below).

### 5.2 Declared Domains empty state (Notion-only)

Replace generic “Linear initiatives/projects required” when:

- Notion connected AND
- Linear not connected AND
- `declared_domain_count = 0`

Copy example:

> No declared work containers yet. Pin one or more Notion databases as work containers in **Integrations → Notion**, then run a declared domain pass.

### 5.3 Declared Domains Data tab

- Seed column: `work_database · notion`
- Link to canon seed + link to Integrations allowlist

---

## 6. API surface

### 6.1 Admin (phase A)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `.../integrations/notion/work-containers` | List databases + pin state |
| `PUT` | `.../integrations/notion/work-containers` | Replace allowlist `{ database_ids: string[] }` |
| `POST` | `.../declared-domains/actions/rebuild` | Full tenant rebuild (see parent plan §12) |

Allowlist update response includes `enqueued_canon_entities`, `enqueued_declared_domain_entities`.

### 6.2 MCP (phase B — with parent Phase 6)

Same list/detail/growing APIs; domains include `work_database` kind.

---

## 7. Backfill & deploy behavior

### 7.1 New deploy (code only)

**Does not** auto-process all canon. Same as Linear:

- Seeds appear only after materialize stamps `declared_container_kind`
- Existing Notion DB canon rows **lack** kind until allowlist + re-materialize

### 7.2 Fizzer unblock playbook

1. Deploy Notion allowlist feature + migration
2. Admin pins Fizzer’s real roadmap/execution databases (e.g. 2–3 IDs)
3. **Backfill job** runs:
   - Re-materialize all `notion.database` raw rows for pinned IDs
   - Re-materialize `notion.database_row` rows for those DBs (set `database_id`)
   - Enqueue declared domain seeds + members
4. Manual or scheduled **RUN DECLARED DOMAIN PASS** (drain) once
5. Domains appear; graph expansion fills cross-tool links when graph caught up

### 7.3 `prepare_notion_declared_container_backfill(tenant_id)`

New helper in `canon/` or `declared_domains/`:

```text
FOR each pinned database_id:
  enqueue canon re-materialize for database raw row
  enqueue canon re-materialize for all database_row raw rows with that database_id
  enqueue declared_domain_entity(seed, extractor_bump)
```

Optional: one-shot admin “Rebuild declared domains” clears `declared_domain_*` for tenant and replays from seeds (parent plan §12).

---

## 8. Rollout phases

### Phase N0 — Schema & config (1 PR)

- Migration: `notion_connection_details.work_container_database_ids text[] default '{}'`
- `declared_container_kind_for_materialize()` with allowlist parameter
- Wire `materialize_raw_row` to load allowlist for connection
- Unit tests: pinned DB gets kind; unpinned does not

### Phase N1 — Row attrs + Level 0 (1 PR)

- `notion_mapper`: `database_id` on rows
- Registry `work_database` membership path
- Integration test: pinned DB + rows → domain + memberships
- Regression: unpinned DB → 0 domains

### Phase N2 — Admin allowlist UI (1 PR)

- Integrations UI pin list
- Empty state copy on Declared Domains
- PUT allowlist → backfill enqueue

### Phase N3 — Rebuild + ops (1 PR)

- `POST .../declared-domains/actions/rebuild` (parent plan deferred item)
- Pass stats: `memberships_superseded`, `seeds_stamped`
- Docs update in `declared-domains-v1-plan.md` §7.1.1 → “shipped: allowlist”

### Phase N4 — Validation

- **Fizzer** (Notion-only): pin DBs → domains > 0 → EM review
- **Multi-tool tenant**: Notion DB domain + Linear project domain coexist (overlap visible)

---

## 9. Explicit non-goals (V1.1)

| Item | Why defer |
|------|-----------|
| Auto-seed all `notion.database` | Garbage domains |
| Infer work DB from title (“Roadmap”, “Sprint”) | Non-deterministic |
| Notion **page** as seed (non-database) | No stable container semantics |
| `work_item` entity type for every row | Optional V1.2; `document` + `database_id` is enough |
| Emergent Domains | Different product layer |
| AI clustering of pages | Emergent / intelligence |

---

## 10. Success criteria

| Tenant | Before | After N1–N3 |
|--------|--------|-------------|
| Fizzer (Notion-only) | 0 domains | ≥1 domain per pinned work DB |
| Linear + Notion | Linear domains only | Both Linear and pinned Notion domains |
| Notion connected, nothing pinned | 0 domains (clear CTA) | Same, with actionable empty state |
| Unpinned CRM database | Not a domain | Still not a domain |

**Trust check:** EM can click a domain → see rows with `direct.container_ref` + evidence `database_id:<uuid>` → matches their Notion backlog.

---

## 11. Open decisions (resolve in N0 design review)

1. **Allowlist storage:** `text[]` on `notion_connection_details` vs JSONB `{ database_ids, pinned_at, pinned_by }` per id for audit?
2. **Max pins per tenant:** Cap at 50? (prevent accidental “pin everything”)
3. **Row re-ingest scope:** On pin, re-materialize from latest raw only vs trigger Notion sync for that database?
4. **Default for new Notion connect:** Empty allowlist + onboarding prompt vs “suggest databases” (display only, no auto-pin)?

**Recommendation:** JSONB array of `{ id, label_snapshot, pinned_at }`, cap 30, re-materialize from existing raw first (fast), optional “Sync this database” button.

---

## 12. Summary

Notion-primary companies **can** use Declared Domains without Linear — but only after **explicit, deterministic qualification** of which databases are work containers. The smallest shippable path is a **per-connection database allowlist** in Integrations, plus `database_id` on row canon attrs and a **backfill on pin**.

Declared Domains runtime (pass, dirty queue, stats, graph expansion) stays unchanged. Canon gains a qualified seed path; Fizzer-style tenants go from “empty by design” to “empty until you pin your backlogs.”
