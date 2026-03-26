# Step 3 — Canonical Ontology: Technical Implementation Specification

**Status:** Architecture locked for implementation planning  
**Depends on:** Step 1 (ingestion), Step 2 (connector projections)  
**Feeds:** Step 4 (execution graph), Step 5 (signals), Step 6 (actions)

This document is the **final Step 3 specification before code**. It incorporates reviewed adjustments (enriched artifact spine, temporal relationships, `current_mapping`, container/containment rules, **ontology registries**, **rule provenance on relationships**, **deterministic rebuild**) and records **critical challenges** so implementers avoid known pitfalls.

**Document version:** 1.2

**Companion:** [Step 3 debugging, monitoring, and execution](step-3-debug-monitoring-and-execution.md) — canonical **debug API** (including **subgraph** + **status**), **confirmed pipeline** (sync → Step 2 → Step 3 + safety net), and **lag metrics**.

---

## Part A — Critical review of proposed adjustments

### A1. Enriched artifact spine (`title` / `summary`, `status`, `last_observed_at`)

**Agreement (directionally correct):** Product queries, signals, and debug UIs need a **display layer** without joining every extension table. `last_observed_at` aligns with “observed execution state” and matches projection semantics.

**Challenges:**

1. **`status` on the spine** is the riskiest column. Kinds disagree on vocabulary (`open`/`closed` vs `merged` vs `draft` vs Notion “archived”). A single `status` string invites **semantic collision** and **stale denormalization** if extensions also store status.
   - **Mitigation:** Treat spine `status` as an **optional display/normalized hint** updated **only** from the canonical writer for that kind, **or** restrict to a **small cross-tool enum** where values are explicitly mapped per `kind` (with many NULLs). Prefer **nullable** + documented per-kind mapping; never require every kind to fill it.

2. **Denormalization drift:** `title`/`summary` must be updated in the **same transaction** as extension rows when Step 3 derives from projections, or define spine fields as **read-through cache** with a single update path.

3. **`title` vs `summary`:** Consider **one** `display_label` (TEXT) plus optional `summary` (TEXT) to avoid duplication—or keep both if product needs short title + long body preview.

**Verdict:** **Adopt** enriched spine with **`title` or `display_label`**, optional **`summary`**, optional **`status`** (nullable, kind-specific semantics), **`last_observed_at`**, plus existing `created_at`. Document **single writer** rules.

---

### A2. Relationship temporal fields (`valid_from`, `valid_to`)

**Agreement:** Execution structure **does** change (PR closes issue → reopen). Without temporal bounds, history is wrong and signals double-count.

**Challenges:**

1. **Model choice:** `valid_to` **SET** when relationship ends vs **append-only supersession** (new row, old row unchanged). Both are valid; **valid_from/valid_to** is efficient for “as-of” queries if **closed intervals** are enforced (`valid_to IS NULL` = current).

2. **Re-open / flip-flop:** A PR that closes an issue twice yields **two** `closes` relationships with non-overlapping intervals, or one row with updated validity—prefer **multiple rows** + non-overlapping `[valid_from, valid_to)` for audit clarity, **or** one row with version—**document one strategy**.

3. **Source of truth for times:** Prefer **connector timestamps** from projections (`github_updated_at`, event time) over ingest wall clock for `valid_from` where available.

4. **Bi-temporal:** Valid-time + transaction-time is **out of scope** for v1 unless compliance requires it.

**Verdict:** **Adopt** `valid_from` (NOT NULL) and `valid_to` (NULL = open-ended). **Append invalidation** as setting `valid_to` + optional new row for the next assertion—pick one rule and stick to it in the implementation plan.

---

### A3. `mapping_event` + `current_mapping`

**Agreement:** Append-only history + fast current lookup is standard and **preserves determinism** if `current_mapping` is **only** derived from events (no ad hoc edits).

**Challenges:**

1. **Single writer invariant:** Any code path that updates `current_mapping` **must** go through **apply_mapping_event(...)** so replay from empty DB reproduces the same `current_mapping`.

2. **Dual target:** Mappings point to **artifact** or **actor**. `current_mapping` rows should use **nullable `artifact_id` / `actor_id`** with **CHECK** that exactly one is set (or separate tables—**one table with discriminator** is acceptable if documented).

3. **Rebuild job:** Ability to **truncate `current_mapping`** and **replay `mapping_event` ORDER BY** (tie-breaker) must be tested—operational safety net.

**Verdict:** **Adopt** as specified; enforce **derived-only** semantics for `current_mapping`.

---

### A4. Actor semantics: relationships vs types

**Agreement:** **Roles** (author, owner, reviewer) are **contextual** and belong on **relationships**. **`kind`** (person, team, bot, service_account) is **intrinsic classification**—keep both: **kind ≠ role**.

**Challenge:** Do not remove **kind** in favor of only edges—**bots vs people** matters for automation and policy without inferring from graph.

**Verdict:** **Polymorphic `actor` with `kind`** + **relationship-typed roles** is the right split.

---

### A5. Container hierarchy and `part_of`

**Agreement:** **Containers vs contained** as distinct kinds + **`part_of` (or `contained_in`)** edges is the right default for Slack (channel/thread/message), repos, PR/commit **at the product/API level**.

**Challenges:**

1. **Git theory:** A **commit** is not always **physically contained** in a PR ref-only; GitHub’s model is “commits **associated with** PR.” Prefer relation types **`associated_with`** / **`introduced_in`** where **`part_of`** would lie. Reserve **`part_of`** for strict trees (message in thread, page in workspace).

2. **Notion:** Deep **parent_page** trees—**`part_of`** chains work; may need **ordering** (`position`) on relationship metadata JSON for siblings—v1 can defer.

3. **Multiple parents:** Rare; use **many edges** or **deny** multiple `part_of` of same type per child—document.

**Verdict:** **Adopt** container/contained kinds + edges; **use precise relation types** so “commit in PR” is not oversimplified as `part_of` if the team prefers accuracy.

---

### A6–A8. Ontology recap, determinism, graph

- **Recap:** Use **registry tables** (`artifact_kind`, `relation_kind`) instead of hardcoded DB enums so new connectors extend the ontology via **data + migrations** (new rows / new extension tables), not PostgreSQL enum ALTER churn.
- **Determinism:** **Risk** if `valid_from` uses wall-clock “now” inconsistently—**bind to projection timestamps and ordered event application**. **Risk** if `current_mapping` is updated outside the event pipeline.
- **Graph:** **Actor + Artifact nodes, Relationship edges** is **sufficient** for Step 4 to **import** or **query** without a second edge store. Step 4 adds **derived** nodes/edges and **materializations** for analytics.

---

## Part B — Final Step 3 ontology (primitives)

| Primitive | Description |
|-----------|-------------|
| **ArtifactKind** (registry) | Allowed artifact kinds (`trackable_unit`, `changeset`, …); metadata includes **`is_container`**. |
| **RelationKind** (registry) | Allowed relationship types; constrains **subject** / **object** endpoint kinds (`actor` vs `artifact`). |
| **Actor** | Tenant-scoped identity for any acting entity (`kind`: person, team, bot, service_account, …). |
| **ActorExternalIdentity** | Link actor ↔ connector-native id + metadata. |
| **Artifact** | Spine row: stable id, **FK → artifact_kind**, display fields, optional status, temporal observation fields. |
| **Artifact extensions** | 1:1 tables: `trackable_unit`, `changeset`, `revision`, `repository`, `document`, `conversation`, `message`, `alert`, … |
| **ExternalReference** | Stable external key (connector + native id + optional projection pointer). |
| **MappingEvent** | Append-only: external ref → actor or artifact, rule version, effective time. |
| **CurrentMapping** | **Derived** fast lookup; **never** authoritative over event history. |
| **Relationship** | Polymorphic subject/object (Actor | Artifact), **FK → relation_kind**, provenance, confidence, **valid_from/valid_to**, **`rule_version` / `rule_source`** when produced by rules. |

**Relationship types** are **rows in `relation_kind`**, not PostgreSQL enums—includes structural (`part_of`, `associated_with`) and semantic (`closes`, `authored_by`, `owns`, …).

---

## Part C — Database schema outline

### C0. Ontology registries (Adjustment 1)

#### `artifact_kind`

| Column | Type | Notes |
|--------|------|--------|
| `id` | SMALLSERIAL / SMALLINT PK | |
| `name` | TEXT UNIQUE NOT NULL | Stable slug: `trackable_unit`, `changeset`, `repository`, … |
| `description` | TEXT | Human-readable |
| `is_container` | BOOLEAN NOT NULL DEFAULT false | True for kinds that **may** contain others (conversation, repository, …) |

**Seed data** in migration: initial kinds for v1 (GitHub path). **New connectors** add rows (and often new **extension tables**) via migration.

#### `relation_kind`

| Column | Type | Notes |
|--------|------|--------|
| `id` | SMALLSERIAL / SMALLINT PK | |
| `name` | TEXT UNIQUE NOT NULL | Stable slug: `authored_by`, `closes`, `part_of`, … |
| `description` | TEXT | Optional |
| `subject_kind` | TEXT NOT NULL | Endpoint class: `actor` or `artifact` (v1). Extensible later (e.g. constrain to specific artifact kinds). |
| `object_kind` | TEXT NOT NULL | Same |

**CHECK:** `subject_kind` and `object_kind` ∈ allowed set for v1 (`actor`, `artifact`). Relax or replace with FK to an **`endpoint_kind`** table if the model grows.

**Validation:** Application (or DB trigger) ensures **`relationship`** rows only use `(subject_type, object_type)` pairs **compatible** with the **`relation_kind`** row (e.g. `authored_by` → actor → artifact).

---

### C1. `actor`

| Column | Notes |
|--------|------|
| `id` | UUID PK |
| `tenant_id` | FK |
| `kind` | text / small registry—**optional future:** FK `actor_kind` table for symmetry with artifacts |
| `display_name` | nullable, human label |
| `created_at`, `updated_at` | server timestamps |

Optional later: `merged_into_actor_id`, merge metadata via **events** preferred.

### C2. `actor_external_identity`

| Column | Notes |
|--------|------|
| `id` | UUID or BIGSERIAL |
| `tenant_id` | |
| `actor_id` | FK → actor |
| `connector` | text |
| `external_id` | stable string per connector contract |
| `traits_json` | optional (login, email hash, …) |
| `first_seen_at`, `last_observed_at` | |

UNIQUE `(tenant_id, connector, external_id)`.

### C3. `artifact` (spine)

| Column | Notes |
|--------|------|
| `id` | UUID PK |
| `tenant_id` | FK |
| `artifact_kind_id` | FK → **artifact_kind** |
| `title` or `display_label` | nullable TEXT |
| `summary` | nullable TEXT |
| `status` | nullable TEXT—per-kind semantics in docs |
| `created_at` | |
| `last_observed_at` | from Step 2 / mapping pipeline |

### C4. Artifact extension tables (1:1 `artifact_id` PK/FK)

Examples (columns illustrative):

- **`trackable_unit`:** provider hints, key, url, …
- **`changeset`:** repo ref, number, head_sha, …
- **`revision`:** sha, …
- **`repository`:** full_name, github_id, …
- **`document`**, **`conversation`**, **`message`**, **`alert`**: as needed per connector

**Rule:** Rich / connector-specific fields live here; spine holds **query-friendly** denormalized fields only.

### C5. `external_reference`

| Column | Notes |
|--------|------|
| `id` | UUID |
| `tenant_id` | |
| `connector` | |
| `resource_type` | optional, for routing |
| `external_key` | normalized stable key |
| `connection_id` | optional FK to tenant connection |
| `last_projection_row_id` | optional pointer to Step 2 row for evidence |

UNIQUE where appropriate `(tenant_id, connector, external_key)` or include `connection_id` if keys collide across connections.

### C6. `mapping_event` (append-only)

| Column | Notes |
|--------|------|
| `id` | BIGSERIAL |
| `tenant_id` | |
| `external_reference_id` | FK |
| `artifact_id` | nullable |
| `actor_id` | nullable |
| `rule_version` | text or semver |
| `effective_at` | timestamptz—prefer connector/projection time |
| `supersedes_event_id` | optional |
| `payload_hash` | optional integrity |

CHECK: exactly one of (`artifact_id`, `actor_id`) non-null per event type, or use separate event types—**document**.

### C7. `current_mapping` (derived)

| Column | Notes |
|--------|------|
| `external_reference_id` | PK |
| `tenant_id` | |
| `artifact_id` | nullable |
| `actor_id` | nullable |
| `updated_at` | |

Same CHECK as mapping target. **Updated only** by deterministic replay / event applier.

### C8. `relationship` (with rule provenance — Adjustment 2)

| Column | Notes |
|--------|------|
| `id` | UUID |
| `tenant_id` | |
| `subject_type` | `actor` \| `artifact` |
| `subject_id` | UUID |
| `object_type` | `actor` \| `artifact` |
| `object_id` | UUID |
| `relation_kind_id` | FK → **relation_kind** |
| `source` | asserted_connector, rule, user, … |
| `confidence` | 0–1 nullable |
| `evidence_ref` | text/json—projection row id, URL, rule id |
| **`rule_version`** | TEXT **NULL** when `source` is direct connector evidence; **NOT NULL** when `source = rule` (or when row was produced by a deterministic rule module) |
| **`rule_source`** | TEXT **NULL** when not rule-generated; otherwise module id, e.g. `github_relationship_rules@v1` |
| `valid_from` | timestamptz NOT NULL |
| `valid_to` | timestamptz NULL = open |
| `created_at` | |

**Invariant:** If `source = rule` (or equivalent), **`rule_version` and `rule_source` MUST be set** so replay can reload the same rule bundle and regenerate identical relationships.

**Connector-only rows:** `rule_version` / `rule_source` NULL; `evidence_ref` points at Step 2 / raw row.

Indexes: `(tenant_id, subject_type, subject_id)`, `(tenant_id, object_type, object_id)`, `(tenant_id, relation_kind_id)`, partial index `WHERE valid_to IS NULL` for “current” edges.

**Optional:** `relationship_metadata` JSONB for ordering, labels—keep thin in v1.

---

## Part D — Relationship model specification

- **Endpoints:** Polymorphic **Actor** and **Artifact** only (v1). **Message** is an **Artifact** kind, not a third node type.
- **Relation vocabulary:** **`relation_kind`** registry defines allowed **`name`** and **(subject_kind, object_kind)** constraints.
- **Temporal semantics:** `[valid_from, valid_to)` half-open intervals; **no overlap** for the same **(subject, object, relation_kind)** if representing a single evolving fact—**or** allow overlap only if semantics differ—**implementation plan must fix one rule**.
- **Assertion vs retraction:** Closing validity = **set `valid_to`**; optional new assertion row for the new state.
- **Step 3 scope:** **Asserted** relationships only (from API, deterministic parsing, explicit rules). **Derived** (blocked-by inference, initiative rollup) → Step 4+.

---

## Part E — Actor identity model

- **One `actor` row per canonical actor**; **merge** produces **events** (`actor_merge_event` or mapping-style) + redirect **or** `merged_into_actor_id` updated only via those events.
- **External identities** never silently merge; **`equivalence_claim`** optional with confidence for cross-tool “same human” before merge.

---

## Part F — Artifact mapping strategy

1. **Ingestion order:** Process Step 2 changes in **`replay_sequence`, `id`** order (same as projections).
2. **Rules:** Versioned modules per connector (`github_mapping@v1`).
3. **Flow:** Upsert `external_reference` → emit **`mapping_event`** → update **`artifact` spine + extension** → **`current_mapping`**.
4. **Idempotency:** Same external ref + same rule version + same payload hash → no duplicate event **or** duplicate events with dedup key—**implementation must choose** (recommend **idempotent mapping_event hash**).

---

## Part G — Determinism guarantees

| Rule | Description |
|------|-------------|
| **Ordered inputs** | Step 3 consumers read projections (or raw) in **replay order**. |
| **Versioned rules** | `rule_version` on every mapping event; code loads rules by version. |
| **Append-only assertions** | Mapping and relationship **changes** are **new rows** or **validity closure**, not silent UPDATE of historical meaning. |
| **`current_mapping`** | **Derived** from `mapping_event` stream only. |
| **Time fields** | Prefer **connector timestamps** for `valid_from` / `effective_at` where available. |
| **No randomness** | ML-based linking **out of core deterministic path** for v1—or writes **candidates** only, not canonical rows. |
| **Rule-generated edges** | **`rule_version` + `rule_source`** on `relationship` when not direct evidence—enables **bit-identical regeneration** under replay. |

**Failure modes:** Manual DB edits to `current_mapping` or `artifact` without events **break** determinism—**forbid in ops** or add migration repair that replays events.

---

## Part G2 — Deterministic rebuild from scratch (Adjustment 3)

This section makes **operational recovery** and **CI replay tests** first-class.

### G2.1 Preconditions

- Step 1–2 data unchanged (or restored from backup).
- **Rule bundles** referenced by `mapping_event.rule_version` and `relationship.rule_version` / `rule_source` are **available** (pinned packages or git tags).

### G2.2 Rebuild procedure (logical)

1. **Truncate** Step 3 mutable/derived outputs for the scope being rebuilt (tenant-wide or single connection):
   - `current_mapping`
   - Optionally **`relationship`** rows for that scope if relationships are **fully regenerated** from rules + evidence (see below).
   - **Do not** delete `mapping_event` until you intend a **full** canonical reset—usually rebuild **from events**, not delete events.

2. **Replay `mapping_event`** in strict order: **`ORDER BY effective_at ASC, id ASC`** (or `(effective_at, id)` as tie-breaker—**must match** the original writer).

3. **Recompute `current_mapping`:** For each `external_reference_id`, apply events in order; last event wins **or** supersession rules as documented. Result must match incremental updates.

4. **Artifacts:** Spine + extensions should be updated **as part of** mapping replay (same transaction per batch as today). If artifacts are **only** created via mapping pipeline, **truncate artifact/extension rows** for the scope and **re-derive from `mapping_event` + external_reference** in the same replay pass **or** rebuild from projections again (alternative: **replay projections** through mapper without deleting `mapping_event`).

5. **Relationships — two supported strategies** (pick one for production):

   - **Strategy A — Event-sourced relationships:** Store **relationship_assertion** append-only events; rebuild `relationship` from them. (Heavier schema; maximum audit.)
   - **Strategy B — Regenerate from projections + rules (recommended v1):** **Delete** `relationship` rows for scope, then **re-run** the Step 3 relationship pass over **Step 2 projections** in **`(last_replay_sequence, last_raw_record_id)` order** (or raw `replay_sequence, id`) with **pinned `rule_version` / `rule_source`**. Output must match if inputs and rules are identical.

6. **Ordering guarantee:** Relationship and mapping generators **must** consume Step 2 rows in the **same total order** as Step 2 replay contract: **`ORDER BY replay_sequence ASC, id ASC`** on `raw_ingestion_records`, or equivalent order on projection tables (**`last_replay_sequence`, artifact line order**—define one canonical ordering for projection-only replay).

7. **Verification:** Hash snapshots (row counts, checksums of sorted `(id, payload_hash)` tuples) **before/after** rebuild for a fixed fixture DB.

### G2.3 What “identical Step 3 output” means

Given the **same** Step 1–2 history and **same** rule versions, **rebuild produces the same** `artifact` rows, `current_mapping`, and `relationship` rows (including temporal fields), modulo **new UUIDs** if IDs are regenerated—**prefer stable IDs** derived from external keys where possible to make byte-identical dumps feasible.

---

## Part H — Graph compatibility (Step 4)

- **Nodes:** `actor.id` and `artifact.id` are **stable node IDs** in a property graph mental model.
- **Edges:** `relationship` rows **are** edges with temporal properties.
- **Step 4:** Adds **derived** graph layers (materialized views, graph DB export, initiative nodes, inferred dependencies)—**does not replace** Step 3 asserted structure.

---

## Part I — Step 3 v1 implementation scope (minimal but correct)

**In scope:**

1. Schema: registries **`artifact_kind`**, **`relation_kind`**; `actor`, `actor_external_identity`, `artifact` (+ enriched spine, **FK artifact_kind_id**), extensions for **Repository**, **TrackableUnit**, **ChangeSet**, **Revision** (GitHub-first).
2. `external_reference`, `mapping_event`, `current_mapping`.
3. `relationship` with **valid_from/valid_to**, **FK relation_kind_id**, **`rule_version` / `rule_source`**, asserted types from GitHub projections + rules **v1**.
4. Deterministic pipeline: **projection row → mapping events → artifacts → relationships** in replay order.
5. Rule bundle **`github_canonical@v1`** pinned.

**Out of scope v1:**

- Slack, Jira, Linear, Notion, Sentry (add **registry rows** + extensions later).
- Probabilistic identity merge, ML linking.
- Bi-temporal auditing beyond `valid_from`/`valid_to`.
- Separate graph database—relational tables suffice.

---

## Part J — Migration plan from Step 2 projections

1. **Backfill or forward-only:** Either **one-time migration job** reads existing `github_*` projections in replay order, or **run Step 3 worker** after each projection batch (similar to Step 2 drain)—**recommend** same **cursor per tenant/connection** on `github_*` / `external_reference` replay position.
2. **Ordering:** Use **`replay_sequence`, `id`** on raw rows **or** deterministic order on projection tables (if processing projections, define order: e.g. by `last_replay_sequence`, `last_raw_record_id`).
3. **Idempotency:** Re-running migration must **not** duplicate artifacts—**external_reference** uniqueness + mapping event dedup.
4. **Validation:** Row counts / spot checks: every projected GitHub entity has **external_reference** + **artifact** + **current_mapping**.

---

## Part K — Risks if Step 3 is wrong (reminder)

| Risk | Mitigation |
|------|------------|
| Spine `status` becomes meaningless soup | Per-kind semantics + nullable + single update path |
| `current_mapping` edited by hand | Ops contract + replay rebuild |
| `part_of` misused for Git graph | Use precise relation types |
| Temporal edges overlap incorrectly | Document interval rules + tests |
| Ontology creep in one table | Kinds + extensions + **registries** + versioned rule bundles |
| Registry drift | Migrations seed new kinds; code validates FKs |

---

## Part L — Canonical debugging interface, execution triggers, and backlog monitoring

This part summarizes **developer observability** and **runtime placement** for Step 3. Full API shapes, metrics names, and the confirmed execution chain are in **[step-3-debug-monitoring-and-execution.md](step-3-debug-monitoring-and-execution.md)**.

### L1. Execution model (confirmed)

1. **Connector sync** (Step 1 ingestion for the connection)  
2. **Step 2 projection drain** (materialize / update connector projections)  
3. **Step 3 canonical drain** (mapping, artifacts, relationships from projections in replay order)  

**Primary trigger:** Run Step 3 **after** a successful Step 2 drain for the same `(tenant_id, connection_id, connector)` scope.

**Safety net:** A **scheduled** (or periodic) Step 3 job **drains backlog** when the post–Step 2 path failed or was skipped—so processing is self-healing without manual runs.

### L2. Debugging interface (table + graph)

- **Prefix:** `/debug/canonical/...` (tenant-scoped, same auth posture as other debug routes).  
- **Table explorer:** Paginated lists and detail routes for actors, artifacts, relationships, external references, mappings, with **neighbor bundles** on detail to avoid N+1 UI calls.  
- **Graph mode (optional v1 UI, API designed first):**  
  `GET /debug/canonical/subgraph?artifact_id={uuid}&depth=2` (or `actor_id=`) returns **`nodes`** and **`edges`** for a bounded subgraph (BFS by depth, caps on depth and node count) for Cytoscape.js or D3.  
- **Status / lag:**  
  `GET /debug/canonical/status` exposes **`step3_last_processed_replay_sequence`**, **`step3_last_processed_id`**, **`step3_lag_rows`**, **`step3_last_processed_timestamp`** (and optional Step 2 watermarks) so developers can verify Step 3 is keeping up with projection backlog.

### L3. Why this matters

Observability on the **ontology layer** catches wrong `relation_kind`, broken containment, and mapping drift **early**. Without it, “wrong graph” bugs are often indistinguishable from ingestion or ordering bugs—see the companion doc for the full checklist.

---

## Step 3 Implementation Plan

This section is the **engineering plan** for implementing Step 3 (no application code in this document).

### SP1. Schema migrations required

1. **Registry tables:** `artifact_kind`, `relation_kind` + seed rows for GitHub v1 kinds and relation kinds.
2. **Core tables:** `actor`, `actor_external_identity`, `artifact` (with **`artifact_kind_id`**), extension tables (`trackable_unit`, `changeset`, `revision`, `repository`, … as needed).
3. **Mapping:** `external_reference`, `mapping_event`, `current_mapping` (with CHECK constraints).
4. **Relationships:** `relationship` with **`relation_kind_id`**, `valid_from`, `valid_to`, `source`, `confidence`, `evidence_ref`, **`rule_version`**, **`rule_source`**, indexes per Part C.
5. **Optional operational tables:** `step3_projection_cursor` (or reuse pattern from Step 2) keyed by `(tenant_id, connection_id, connector)` for incremental processing—**if** processing is cursor-based.

All migrations **Alembic**; registries seeded in **same revision** or follow-up data migration with idempotent `INSERT … ON CONFLICT DO NOTHING`.

### SP2. Step 3 processing pipeline

| Stage | Input | Output |
|-------|--------|--------|
| **Read** | Step 2 projection rows (or raw) in replay order | Batches |
| **Resolve** | Connector + external key | `external_reference` |
| **Map** | Reference + rule bundle | `mapping_event`, `artifact` + extensions, `current_mapping` |
| **Relate** | Projections + registry + rule bundle | `relationship` rows (connector-evidence and rule-generated), temporal fields |
| **Commit** | Per batch transaction | Durability |

**Placement:** Run as **worker** after Step 2 drain (analogous to projection worker) **or** batch job; **must** respect single-writer / lease per scope if concurrent.

**Triggers:** (1) **Post–Step 2 drain** for the same connection—primary path. (2) **Scheduled / periodic** Step 3 drain as a **safety net** for lag or missed runs. See **Part L** and [step-3-debug-monitoring-and-execution.md](step-3-debug-monitoring-and-execution.md).

### SP3. Modules / components to implement

| Area | Responsibility |
|------|----------------|
| **`vector.domains.canonical.registries`** | Load/cache `artifact_kind`, `relation_kind`; validate FKs |
| **`vector.domains.canonical.mapping`** | `external_reference` upsert, `mapping_event` append, `current_mapping` apply |
| **`vector.domains.canonical.artifacts`** | Create/update spine + extension rows from mapping |
| **`vector.domains.canonical.relationships`** | Assert edges; set `valid_from`/`valid_to`; set `rule_*` when `source=rule` |
| **`vector.domains.canonical.rules.github`** | `github_mapping@v1`, `github_relationship_rules@v1` — pure functions + version string |
| **`vector.infrastructure.db.repositories.canonical_*`** | Persistence adapters |
| **`vector.contracts.debug_canonical` (or similar)** | HTTP routes under `/debug/canonical/`: entity lists, detail, **`GET /subgraph`**, **`GET /status`** (lag metrics); optional rebuild trigger later |

### SP4. Replay and cursor strategy

- **Cursor:** `(last_replay_sequence, last_raw_record_id)` or **raw** `(replay_sequence, id)` if reading from `raw_ingestion_records`—**must align** with Step 2 ordering contract.
- **Per scope:** `(tenant_id, connection_id, connector)` for GitHub v1.
- **Batch size:** Configurable (e.g. 200–1000 rows).
- **Transaction:** One transaction per batch: mapping + artifacts + relationships + cursor advance **or** split with clear ordering if relationships depend on artifacts created in-batch.

### SP5. Idempotency guarantees

- **External reference:** Unique key prevents duplicate refs.
- **Mapping events:** Dedup key `(external_reference_id, rule_version, payload_hash)` or **skip** if already applied—document.
- **Artifacts:** Upsert by canonical identity (from mapping), not random UUIDs if stability desired.
- **Relationships:** Idempotent **upsert** on natural key **(subject, object, relation_kind_id, valid_from)** or **close-then-insert** pattern for temporal updates.

### SP6. Test strategy

| Layer | Tests |
|-------|--------|
| **Unit** | Rule modules: given fixture projection JSON → expected mapping events / relationships |
| **Integration** | DB: replay small fixture twice → identical `current_mapping` and relationship counts |
| **Rebuild** | Truncate derived tables → replay `mapping_event` + regenerate relationships → match golden snapshot |
| **Ordering** | Shuffle input batch order (wrong) → assert **different** outcome or explicit failure |

### SP7. Operational rebuild procedure

1. **Pause** Step 3 writers for tenant/connection (lease / feature flag).
2. **Truncate** `current_mapping`; optionally `relationship` for scope; optionally artifacts if full rebuild from projections.
3. **Replay** `mapping_event` OR **re-ingest** from Step 2 order into mapper with pinned rules.
4. **Regenerate** relationships per Part G2.
5. **Verify** checksums / counts.
6. **Resume** workers.

Document **runbook** in ops docs; include **rollback** (restore DB snapshot) if rebuild fails mid-way.

---

## Closing assessment

Vector is building a **deterministic execution intelligence** layer: the same ingested evidence and the same rule versions must yield the **same** canonical execution structure—so signals, graph analytics, and future actions rest on **explainable** data, not ad hoc joins.

If Step 3 is implemented with **registries** (extensible ontology), **append-only mapping**, **temporal relationships**, **rule provenance** on edges, and **proven rebuild** semantics, then GitHub + Jira + Slack + CI/CD can converge to **one execution model** and **one delivery graph** without sacrificing connector fidelity (Step 2) or auditability (Step 1). That foundation is what enables Steps 4–6 to be credible.

---

**Next step:** Implement schema migrations and the GitHub v1 rule bundle per **Step 3 Implementation Plan** above; wire **post–Step 2 → Step 3 drain**, **scheduled safety-net drain**, and **`/debug/canonical`** routes (including **subgraph** + **status**) per **[step-3-debug-monitoring-and-execution.md](step-3-debug-monitoring-and-execution.md)**.
