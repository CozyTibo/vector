# Cortex Canonization — Ingestion Discovery & Grounded Plan (v1)

**Status:** draft — grounded in codebase as of 2026-05-28  
**Audience:** engineers building canonization after ingestion-only substrate collapse  
**Scope (v1):** deterministic canonized execution substrate only — Slack, GitHub, Linear, Notion  
**Supersedes (for execution):** treat `DOCS/cortex/03-canonical/implementation-plan.md` (18-stage program) as **historical** until reconciled.

**Code anchors:**

- Ingestion: `backend/src/vector/domains/cortex/ingestion/`
- Raw persistence: `raw_ingestion_records`, `raw_memory_*` indexes
- Post-ingest hook: `post_ingestion_refresh_dispatch.py` → `substrate_pipeline_removed` (no-op)
- Substrate drop: `backend/alembic/versions/20260528_0097_drop_cortex_substrate_phases_02_08.py`
- Exhaust matrix: `exhaust_coverage_registry.py`, `DOCS/cortex/connectors/connector-exhaust-matrix.md`

---

## Architectural decision — reduced scope (v1)

**Cortex v1 stops at:**

- Deterministic canonized execution substrate
- Normalized materialized entities
- Provenance-preserving reconstruction

**Cortex v1 does NOT build:**

- Identity resolution
- Organizational graph
- Semantic relationship inference
- Execution intelligence
- Probabilistic entity merging
- Graph traversal infrastructure

Those are **later layers** once the substrate is stable.

### Cortex is not a graph system (v1)

Do **not** design with:

- Nodes / edges
- Graph ontology
- Knowledge-graph abstractions
- Generalized edge stores
- Confidence-scored relationships

Design with:

- **Canonized execution artifacts** (normalized rows)
- **Stable references** (FKs, provider ids, parent ids on entities)
- **Timeline reconstruction** (timestamps + ordered materialization)
- **Provenance-backed materialization** (every entity → raw)

A graph, if ever needed, **emerges later** from the canonized substrate — it is not the v1 data model.

### System philosophy

```
raw ingestion
    → canonized deterministic substrate
        → later derivations / intelligence (out of scope)
```

**Not:**

```
raw → graph → ontology → intelligence
```

### Simplified goal

> Create a deterministic, replayable, normalized execution substrate from raw operational exhaust.

The canonization layer should feel **boring**: deterministic, operationally simple, replayable, explainable, easy to inspect manually.

### Canonization constraints (unchanged)

- Independent from ingestion
- Replayable
- Deterministic
- Append-friendly
- Debuggable
- Inspectable

**Workers do only:**

1. Read raw data
2. Normalize entities into substrate tables
3. Preserve provenance and source references

Nothing more.

---

## Executive summary

| Layer | Status |
|--------|--------|
| **Ingestion** | Beat → Celery → `execute_connector_sync` → `append_raw` |
| **Storage** | Append-only `raw_ingestion_records` + lineage / revision / archive indexes |
| **Canonization (v1)** | **Not built**; greenfield substrate tables below |
| **Out of scope (v1)** | Edges, identity merge, graph, MCP intelligence, traversal |

Implementation **stops after Phase 4**. Phases 5+ from earlier drafts are **explicitly deferred**.

---

## Step 1 — Ingestion inventory

*(Discovery reference — unchanged facts about what ingestion produces today.)*

### Shared infrastructure (all connectors)

#### Jobs & scheduling

```
Celery Beat → tick_cortex_ingestion_scheduler
           → iter_routed_live_sync_jobs (min-gap, no duplicate RUNNING)
           → run_cortex_connector_sync_task (queue: cortex_live)
           → execute_connector_sync → run_*_connector_sync → append_raw
```

| Component | Table / module | Role |
|-----------|----------------|------|
| Scheduler tick | `ingestion_scheduler_ticks` | Beat audit |
| Sync run | `ingestion_runs` | Per execution |
| Checkpoint | `connector_sync_state` | JSON cursors (`default` or `replay:<job_id>`) |
| Replay task | `run_cortex_connector_replay_sync_task` | Queue `cortex_replay` |

#### `raw_ingestion_records` (append-only)

| Column | Semantics |
|--------|-----------|
| `id`, `replay_sequence` | PK + global ordering |
| `tenant_id`, `connection_id`, `connector` | Scope |
| `resource_type`, `external_id` | Ingestion family + provider address |
| `payload_body` | JSONB: envelope + provider payload |
| `source_identity_key`, `source_revision_key` | Logical identity (Step 15) |
| `run_id`, `fetched_at`, `replay_job_id` | Provenance |

**Derived indexes:** `raw_memory_lineage_index`, `raw_memory_revision_index`, `raw_memory_archive_catalog`.

#### Envelope & semantics

See `raw_envelope_contract.py`, `live_idempotency.py`, `checkpoint_contract.py`. Ingestion is append-only per logical revision; live dedupe on `(identity, revision)`.

#### Normalization at ingest (taxonomy)

| Kind | Examples |
|------|----------|
| Raw preservation | `message`, `pull_request`, `issue`, `user`, … |
| Partial normalization | envelope, synthetic `slack.thread`, `github.review_thread` |
| **Not done (v1 canon)** | cross-tool identity, substrate entities, graphs |

### Per-connector resource types (summary)

**Slack:** `slack.user`, `slack.conversation`, `slack.channel_member`, `slack.message`, `slack.message_reply`, `slack.thread`, `slack.reaction`, `slack.file`, `slack.pin`, …

**GitHub:** `github.user`, `github.team`, `github.repository`, `github.pull_request`, `github.issue`, reviews, comments, commits, checks, workflows, deployments, releases, …

**Linear:** `linear.user`, `linear.team`, `linear.issue`, `linear.comment`, `linear.project`, `linear.cycle`, …

**Notion:** `notion.user`, `notion.page`, `notion.database`, `notion.database_row`, `notion.block`, …

**Calls:** defer unless explicitly added to v1 mappers.

Full tables: `exhaust_coverage_registry.py`, `connector-exhaust-matrix.md`.

---

## Step 2 — Cross-tool overlap (reference only — not v1 work)

Overlaps (person, team, work item, comment) exist across tools but **v1 does not resolve them**.

| Topic | v1 handling |
|-------|-------------|
| Same person on Slack + GitHub | Separate `canon_entities` per connector scope; no merge |
| Work item across Linear / GitHub / Notion | Separate entity types; link only via **provider fields** on the entity row when present (e.g. URL in Linear attachment stored as attribute, not an edge table) |
| Teams vs channels | Separate entities; membership via FK columns where mapper extracts provider ids |

**Deferred:** alias tables, email matching, organizational topology, inferred links.

---

## Step 3 — Canonized entity types (v1 substrate)

These are **normalized execution entities**, not graph nodes.

| Entity type (substrate) | Typical raw `resource_type` sources |
|-------------------------|-------------------------------------|
| **actor** | `*.user`, `slack.user`, `github.user`, `linear.user`, `notion.user` |
| **conversation** | `slack.conversation`, `slack.thread`, `linear.comment_thread`, `github.review_thread` |
| **message** | `slack.message`, `slack.message_reply`, `linear.comment`, github *comment* / review bodies |
| **work_item** | `linear.issue`, `github.issue` |
| **pull_request** | `github.pull_request` |
| **commit** | `github.commit` |
| **project** | `linear.project`; `notion.database` (as project-like container) |
| **team** | `linear.team` |
| **cycle** | `linear.cycle` |
| **label** | `linear.issue_label` |
| **initiative** | `linear.initiative` |
| **issue_relation** | `linear.issue_relation` (provider link between issues; attrs + optional `work_item_ref`) |
| **document** | `notion.page`, `notion.block`, `notion.database_row` |
| **release** | `github.release` |
| **deployment** | `github.deployment`, `github.workflow_run` (mapper policy: separate or folded per contract) |

**Explicitly out of v1 substrate design:**

- `linear.issue_relation` as a separate **graph edge store** → v1 uses `issue_relation` entities with attrs + `work_item_ref`, not `canon_edges`
- Cross-tool “execution intelligence” or traversal

---

## Step 4 — Canonical model (substrate tables only)

### `canon_entities`

Stable normalized rows. One logical entity per `(tenant_id, entity_type, entity_key)` where `entity_key` is deterministic from connector + resource_type + external_id (same spirit as `source_identity_key`, scoped to tenant).

| Column (conceptual) | Purpose |
|---------------------|---------|
| `id` | Internal UUID (stable FK target for references) |
| `tenant_id`, `connection_id` | Scope |
| `entity_type` | actor, message, work_item, pull_request, … |
| `entity_key` | Deterministic logical key |
| `display_label` | Human-readable (title, name, identifier) |
| `attrs_json` | Small normalized fields (state, status, timestamps copied from provider) |
| `mapper_version` | Canon mapper version that last wrote this row |
| `materialized_at` | Last successful materialization time |

**References between entities (v1):** columns on `canon_entities`, not a separate edge store.

Examples:

- `message.author_entity_id`
- `message.conversation_entity_id`
- `message.parent_message_entity_id`
- `pull_request.repository_entity_id`
- `work_item.assignee_entity_id`
- `document.parent_document_entity_id`

Populate only when the provider payload supplies a **deterministic** id (no inference, no fuzzy match).

### `canon_entity_sources`

Provenance: links each materialized entity (or each materialization revision) to raw truth.

| Column (conceptual) | Purpose |
|---------------------|---------|
| `canon_entity_id` | FK → `canon_entities` |
| `raw_id` | FK → `raw_ingestion_records.id` |
| `connector`, `resource_type`, `external_id` | Source address |
| `source_identity_key`, `source_revision_key` | Align with raw layer |
| `observed_at` | `fetched_at` or provider event time |
| `is_latest` | Whether this source row is the current revision for that entity |

Every canonized entity must be traceable: **entity → canon_entity_sources → raw_ingestion_records**.

Append new source rows on new raw revisions; update `canon_entities` in place or version per mapper policy (prefer: entity row updated, sources appended).

### `canon_dirty_queue`

Independent materialization inbox.

| Column (conceptual) | Purpose |
|---------------------|---------|
| `tenant_id`, `connection_id`, `source_identity_key` | What to process |
| `reason` | `new_raw`, `reprocess`, `mapper_bump` |
| `enqueued_at`, `attempts`, `last_error` | Ops |

### `canon_materialization_cursors`

Progress tracking per tenant (optionally per connector / resource_type).

| Column (conceptual) | Purpose |
|---------------------|---------|
| `last_raw_id` or `last_replay_sequence` | Incremental scan position |
| `mapper_version` | Active mapper |
| `updated_at` | Heartbeat |

### `canon_pass_runs` (observability)

Mirror `ingestion_runs`: one row per canon pass / batch — counts, errors, duration. Supports admin “Passes” tab.

### Removed from v1 schema

| Removed | Reason |
|---------|--------|
| `canon_edges` | Graph abstraction — deferred |
| `canon_observation` as separate ontology | Replaced by `canon_entity_sources` |
| `canon_entity_alias` | Identity resolution — deferred |
| Confidence / inferred relationship columns | Out of scope |

---

## Step 5 — Canonization architecture

```
raw_ingestion_records (+ optional raw_memory_lineage_index hint)
        → canon_dirty_queue
        → canonize worker (Celery: cortex_canon)
        → read raw → map → upsert canon_entities
                        → append canon_entity_sources
        → advance canon_materialization_cursors
```

| Concern | Design |
|---------|--------|
| Independence | Own Beat schedule + queue; no blocking inside `append_raw` (optional async enqueue only) |
| Incremental | Drain dirty queue and/or `raw.id > cursor` |
| Re-canonization | Bump `mapper_version` → re-enqueue identities |
| Replay raw | Exclude `replay_job_id IS NOT NULL` from live canon lane (or separate cursor namespace) |
| Idempotency | Same `(entity_key, source_revision_key, mapper_version)` → no duplicate source rows |
| Debugging | CLI/API: entity id → sources → raw payload JSON |
| Admin (light) | Phase 1: readiness + pass runs; Phase 4: entity list + drilldown (ingestion-parity **minimal**, not full ops suite) |

**Do not build:** substrate FSM, pipeline coordinator, graph projection, synthesis, traversal.

---

## Step 6 — Implementation plan (Phases 1–4 only)

### Phase 1 — Inventory & observability (1–2 weeks)

**Goal:** Understand exactly what ingestion produces operationally.

- Scanner: per-tenant counts by `resource_type`, lineage lag, unmapped types
- DB: `canon_pass_runs`, `canon_materialization_cursors` (metrics only OK initially)
- Admin (basic): canon readiness — raw volume, mapper coverage %, queue depth, last pass (mirror ingestion overview spirit)
- CI: ingestion test suite on PR

**Success:** Operator can answer “what raw exists?” and “what is not yet mappable?” without SQL.

---

### Phase 2 — Raw / source contracts (1 week)

**Goal:** Formalize stable ingestion → canon contracts.

- `canon_resource_type_registry`: map / skip / defer per `resource_type` (aligned with exhaust matrix)
- `CanonMapper` protocol: `raw row → EntityDraft + source metadata`
- Golden fixtures from existing ingestion tests

**Success:** Every ingested `resource_type` has an explicit v1 disposition.

---

### Phase 3 — Canonical entities (2–3 weeks)

**Goal:** Deterministic normalized execution entities with provenance.

- Migrations: `canon_entities`, `canon_entity_sources`, `canon_dirty_queue`
- Mappers v1: actors, messages, conversations, work_items, pull_requests, commits (prioritize execution-critical types)
- FK population only from provider-supplied ids
- Tests: idempotent materialization; entity → raw trace

**Success:** Re-run produces no duplicate entities; every entity has ≥1 `canon_entity_sources` row pointing at raw.

---

### Phase 4 — Canonization workers & schedule (1–2 weeks)

**Goal:** Independently runnable materialization — queues, retries, scheduling, replayability.

- `tick_cortex_canon_scheduler` + `canonize_batch_task` / per-identity task
- Optional: enqueue on lineage upsert (feature flag)
- Admin (basic): recent passes, entity search by `entity_key` / label, drilldown to raw
- **STOP HERE for v1.**

**Success:** Canon runs on schedule without ingestion coupling; lag visible; manual re-run works.

---

## Explicitly deferred (post–Phase 4)

Do not design or implement in the current program:

| Deferred capability | Notes |
|--------------------|--------|
| Identity resolution | Email merge, cross-tool actor unification |
| `canon_edges` / edge store | Use FKs on entities in v1 |
| Relationship extraction | URL parsing, inferred links |
| Graph traversal | OCTS, walk records, etc. |
| Execution graph materialization | Timeline products for agents |
| Organizational topology | Org graph, team equivalence |
| Semantic / probabilistic merging | Any non-deterministic join |
| MCP execution intelligence | Read substrate only after it exists |
| `linear.issue_relation` as first-class edges | Optional attrs on work_item later |

When substrate is stable, a **separate** program may add derivation layers — not an extension of Phase 4.

---

## Risks (v1)

| Risk | Mitigation |
|------|------------|
| Mapper drift | `mapper_version` + golden tests per `resource_type` |
| Queue backlog | Per-tenant fair batches, caps |
| Replay pollution | Separate live vs replay canon cursor |
| Scope creep into graph | This doc is the scope gate; reject edge-table PRs |
| Old `03-canonical` docs | Treat as historical; this file wins for v1 execution |

---

## Related docs

- Raw layer: `DOCS/cortex/02-raw-store/`, `DOCS/cortex/01-ingestion/`
- Historical canon program: `DOCS/cortex/03-canonical/implementation-plan.md`
- Ingestion exhaust: `DOCS/cortex/connectors/connector-exhaust-matrix.md`
- Ingestion admin (pattern reference): `frontend/src/admin/AdminCortexIngestionPage.tsx`

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-28 | Initial grounded discovery + plan |
| 2026-05-28 | **Scope reduction:** substrate-only; no graph/edges/identity; Phases 1–4 only; `canon_entities` + `canon_entity_sources` model |
