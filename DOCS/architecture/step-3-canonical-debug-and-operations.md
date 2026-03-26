# Step 3: Canonical Ontology — Architecture, Debug APIs, and Operations

This document is a **developer-facing architecture reference** for the Step 3 canonical layer: how it fits the ingestion pipeline, what entities exist, how to debug them via HTTP APIs, how the canonical worker runs, how to interpret operational status, and how a minimal debug UI supports validation. It is **not** an implementation backlog.

---

## 1. Current Canonical Architecture

### 1.1 Pipeline context (Steps 1–4+)

| Step | Name | Role |
|------|------|------|
| **1** | Raw ingestion | Append-only capture of connector resources (e.g. GitHub REST) into `raw_ingestion_records`, ordered by global **`replay_sequence`** and row **`id`**. |
| **2** | Connector projections | Idempotent, tenant-scoped materialized views per connector (e.g. GitHub repositories, PRs, issues, commits) derived from raw rows. |
| **3** | Canonical ontology | Cross-connector **execution primitives**: normalized **actors**, **artifacts**, **relationships**, and **mapping** from external references to canonical entities. |
| **4+** | Execution graph / signals / actions | Future product layers that consume the canonical graph (not covered in detail here). |

Step 3 **does not replace** Step 2. It builds a **stable semantic layer** suitable for graph traversal, policy, and downstream automation.

### 1.2 What Step 3 consumes

- **Orchestration** is driven by the **same ordered raw stream** as Step 2 (per `connection_id` + `connector`), so replay is deterministic and comparable across stages.
- **Semantic inputs** for the GitHub mapper are **Step 2 projection rows** (e.g. `GithubPullRequest`, `GithubRepository`) joined in the context of each raw record. The mapper is not intended to re-derive full domain state from raw JSON alone; **projections are the structured source of truth** for mapped fields, while the raw row provides ordering, linkage, and resource typing.

So: **Step 3 consumes projection-backed state, replayed via raw ingestion ordering** — not “raw-only” parsing for GitHub v1.

### 1.3 Core entities

| Entity | Purpose |
|--------|---------|
| **artifact** | Typed work product or container in the execution model (e.g. repository, trackable unit, changeset, revision). Carries titles, status, observation times. |
| **actor** | A participant (e.g. person, bot) with a display identity. |
| **relationship** | A directed edge between two endpoints (**subject** → **object**), each either an **actor** or an **artifact**, labeled by a **relation_kind** (e.g. `authored_by`, `associated_with`). May be time-bounded (`valid_from` / `valid_to`) for history. |
| **external_reference** | Stable handle to an external object (`connector`, `external_key`, optional `last_raw_record_id`) before it is mapped into canonical form. |
| **mapping_event** | Append-only audit of mapping decisions (rule version, effective time, link to external reference and optional artifact/actor targets). |
| **current_mapping** | **Current** resolution from an `external_reference` to at most one **artifact** and/or **actor** — the live “wins” state used for idempotency and navigation. |

**Clarifications:**

- Canonical **artifacts** and **actors** are **execution primitives** (stable IDs, tenant-scoped), not raw API payloads.
- **Relationships** are **structural links** between actors and artifacts (and artifact–artifact where allowed by the relation registry), not arbitrary JSON graphs.
- **external_reference** + **mapping_event** + **current_mapping** together document **how** external data was folded into the ontology and **what** the active mapping is after each update.

---

## 2. Canonical Debug API

All routes are mounted under **`/debug`** (prefix) with path **`/canonical/...`**. In full: **`/debug/canonical/...`**.

**Authentication:** browser **session cookie** (same as the rest of the app). **Authorization:** tenant membership is asserted; responses are scoped to the caller’s tenant.

### 2.1 List endpoints (paginated)

Responses share shape: `{ total, limit, offset, items: [...] }` (`PaginatedResponse`).

| Method & path | Query parameters (typical) | Purpose |
|---------------|----------------------------|---------|
| `GET /debug/canonical/artifacts` | `limit`, `offset`, `artifact_kind_id`, `q` | Browse artifacts; `q` filters title/summary. |
| `GET /debug/canonical/actors` | `limit`, `offset`, `q` | Browse actors; `q` filters display name. |
| `GET /debug/canonical/relationships` | `limit`, `offset`, `current_only` (default `true`) | Browse relationships; set `current_only=false` to include historical (closed) edges. |
| `GET /debug/canonical/external-references` | `limit`, `offset` | Browse external references. |
| `GET /debug/canonical/mapping-events` | `limit`, `offset`, `external_reference_id` | List mapping events; filter by xref to inspect one connector object’s mapping history. |

**Use:** quickly find entities, scan for missing data, and correlate rows with projection/raw debug tools.

### 2.2 Detail endpoints (single resource)

| Method & path | Returns (conceptually) |
|---------------|-------------------------|
| `GET /debug/canonical/artifacts/{artifact_id}` | `artifact` block; **relationships** (summarized with subject/object labels); **external_references** linked via current mapping. |
| `GET /debug/canonical/actors/{actor_id}` | `actor` block; **external_identities**; **relationships** touching this actor. |
| `GET /debug/canonical/relationships/{relationship_id}` | Relationship metadata + subject/object labels. |
| `GET /debug/canonical/external-references/{xref_id}` | External reference, optional **current_mapping**, recent **mapping_events**. |

**Use:** drill-down after lists; verify edges around one artifact or actor; trace mapping for one external key.

### 2.3 Graph: `GET /debug/canonical/subgraph`

**Query:** exactly **one** of `artifact_id` or `actor_id`; optional `depth` (0–4, default 2); `include_historical` (default false, i.e. current relationships only unless overridden).

**Returns:** `SubgraphResponse`: anchor, depth, **nodes** (artifact or actor with labels/kinds), **edges** (relationship id, source/target UUIDs, `relation_kind`, validity), plus `truncated` / `truncation_reason` if limits hit.

**Use:** visualize a **small neighborhood** (e.g. PR + repo + authors + commits) without exporting the full database. Intended for **debug-scale** graphs (server caps node count).

### 2.4 Status: `GET /debug/canonical/status`

**Query:** **`connection_id`** (required, UUID); optional `connector` (defaults to GitHub).

**Returns:** `CanonicalStatusResponse` — see §4.

**Use:** single-call **pipeline health** for Step 3 relative to Step 2’s watermark for that connection.

### 2.5 Manual drain: `POST /debug/canonical/drain`

**Query:** `connection_id`; optional `connector` (default GitHub).

**Behavior:** runs **`drain_github_canonical`** in-process (safety-net / manual catch-up). Returns metrics such as `raw_rows_processed` and `batches_committed`.

**Use:** when automatic drain after sync did not run or backlog must be cleared deliberately (still subject to worker limits).

---

## 3. Canonical Pipeline Execution

### 3.1 End-to-end flow (GitHub)

1. **Connector sync** — e.g. `POST /connectors/github/sync` (Step 1 poll) appends raw rows for the tenant’s GitHub connection.
2. **Step 2 projection drain** — `drain_github_projections` advances connector projection cursors and updates materialized GitHub tables.
3. **Step 3 canonical drain** — `drain_github_canonical` processes **raw rows** in **`(replay_sequence, id)`** order that are **after** the Step 3 cursor and **within** what Step 2 has effectively covered, updating canonical tables and the Step 3 cursor.

The sync handler chains **Step 2 then Step 3** when the ingestion run succeeds, so a normal “sync” keeps projections and canonical layers moving together for that connection.

### 3.2 Worker behavior (`drain_github_canonical`)

- Ensures a **`step3_canonical_cursor`** row exists for `(connection_id, connector)`.
- Loops in batches (default batch size 500, max batches 10_000 per invocation): loads the next raw rows matching GitHub resource types and successful HTTP status, ordered by **`replay_sequence` ASC, `id` ASC**.
- For each row, runs **`handle_github_canonical_row`** (GitHub mapper), which upserts canonical entities and relationships idempotently.
- After each batch, updates the cursor to the **last processed** row’s `(replay_sequence, id)` and sets **`last_processed_at`**.

### 3.3 Cursor and replay ordering

- **Global ordering** matches Step 2’s replay semantics: **`replay_sequence` first**, then raw row **`id`** as tie-breaker.
- **`Step3CanonicalCursor`** stores `last_replay_sequence` and `last_raw_record_id` (the tie-breaker) for `(connection_id, connector)`.

### 3.4 Backlog and “caught up”

- **Backlog** = raw rows that Step 3 has not yet processed, **bounded above** by Step 2’s projection progress (watermark) for the same connection — see `count_canonical_lag` in §4.
- **Safety-net:** `POST /debug/canonical/drain` or a future scheduler can invoke the same drain function if Step 3 falls behind after large imports or failures.

---

## 4. Canonical Operational Monitoring

### 4.1 Endpoint: `GET /debug/canonical/status`

Requires a valid **`connection_id`** for the tenant. The response includes:

| Field | Meaning |
|-------|---------|
| `step3_last_processed_replay_sequence` | Last **`replay_sequence`** committed on the Step 3 cursor for this connection + connector. |
| `step3_last_processed_id` | Tie-breaker raw row **`id`** at that sequence (same ordering as ingestion). |
| `step3_lag_rows` | Count of raw rows **still to process** by Step 3 **up to** Step 2’s watermark — i.e. in the half-open interval **(step3 cursor, step2 watermark]** in replay order, filtered to canonical-eligible GitHub resource types. |
| `step3_last_processed_timestamp` | **`last_processed_at`** on `step3_canonical_cursor` (when the cursor last advanced). |
| `step2_watermark_replay_sequence` / `step2_watermark_id` | Step 2 projection progress (`connector_projection_progress`) for the same scope — useful to compare “how far raw ingestion is committed into projections” vs Step 3. |

### 4.2 How to verify “caught up”

- **`step3_lag_rows == 0`** → Step 3 has processed all raw rows through the current Step 2 watermark (for those resource types).
- If lag is **non-zero** after a successful sync, investigate failed mapper rows, manual drain needs, or Step 2 not advancing.
- Compare **step3** cursor fields to **step2** watermark: if step2 moves forward and lag stays high, Step 3 is behind; if lag is zero, Step 3 is aligned with Step 2’s committed projection boundary.

---

## 5. Canonical Debug Visualization (Frontend Developer Tool)

This is a **developer debugging surface**, not end-user product UI. It should stay **thin**: tables, links, optional small graph, no design-system polish requirement.

### 5.1 Entry

- A dedicated route such as **`/debug/canonical`**, using the same API base and **cookie credentials** as other debug pages.

### 5.2 Suggested layout (tabs)

| Tab | Backing APIs | Purpose |
|-----|----------------|--------|
| **Artifacts** | `GET /debug/canonical/artifacts` | Sortable/filterable list; row → artifact detail. |
| **Actors** | `GET /debug/canonical/actors` | Same pattern for actors. |
| **Relationships** | `GET /debug/canonical/relationships` | Scan edges; cells link to artifact/actor detail routes. |
| **External References** | `GET /debug/canonical/external-references` | Inspect connector keys and linkage to mapping. |
| **Graph** | `GET /debug/canonical/subgraph?artifact_id=…` or `actor_id=…` | Small **depth-limited** (e.g. ≤2) graph visualization (e.g. Cytoscape.js) for local neighborhoods. |
| **Status** | `GET /debug/canonical/status?connection_id=…` | Show **step3_*** fields and connection selector (e.g. from recent ingestion runs). |

**Detail routes** (examples): `/debug/canonical/artifacts/:id`, `/debug/canonical/actors/:id` — calling the detail GETs above; show related relationships, external refs, and aggregated mapping events as needed.

### 5.3 Developer goals

- **Inspect** canonical rows without SQL.
- **Navigate** artifact ↔ actor ↔ artifact via links.
- **Spot-check** ontology shape (relation kinds, artifact kinds) after connector changes.
- **Confirm** pipeline catch-up using the Status tab.

---

## 6. Example Ontology Navigation

These examples match the **relation kinds** seeded for GitHub v1 (e.g. `authored_by`, `associated_with`) and the **artifact kinds** (e.g. `changeset`, `revision`, `repository`).

### 6.1 Pull request (changeset)

```
PR (artifact: changeset)
 ├─ authored_by        → actor (e.g. author)
 ├─ associated_with    → repository (artifact)
 └─ associated_with    → commit(s) (artifact: revision)
```

**Validation:** open the PR artifact detail — outgoing/incoming relationship tables should reflect authorship and associations; subgraph from the PR artifact should show the small cluster.

### 6.2 Commit (revision)

```
commit (artifact: revision)
 ├─ authored_by        → actor
 └─ associated_with    → repository (artifact)
```

**Validation:** same as above using a revision artifact id; cross-check **external_reference** and **mapping_event** rows for the GitHub commit key.

### 6.3 Why this matters

Visual inspection catches **wrong relation direction**, **missing edges**, **duplicate actors**, or **stale mappings** long before product features consume the graph. The debug API + small graph view make regressions in **`github_mapper`** or projection joins obvious.

---

## 7. Developer Usage

### 7.1 Typical validation workflow

1. **Run GitHub sync** (`POST /connectors/github/sync` or equivalent) so Step 1 runs and Step 2 + Step 3 drain on success.
2. **Confirm Step 2 projections** (existing connector projection debug UI or SQL) — entities expected from the sync exist.
3. **Confirm Step 3** — `GET /debug/canonical/status?connection_id=…` → **`step3_lag_rows == 0`** (or run `POST /debug/canonical/drain` if appropriate).
4. **Inspect artifacts** — list + detail; check kinds, titles, and times.
5. **Inspect relationships** — list + artifact/actor detail; verify subject/object and relation kinds.
6. **Visualize a neighborhood** — `GET /debug/canonical/subgraph` from a known artifact or actor id.

### 7.2 When something looks wrong

- **Lag non-zero:** drain not run, mapper error, or Step 2 watermark ahead — use status fields and server logs around `handle_github_canonical_row`.
- **Missing edges:** compare projection rows for the resource vs canonical relationship list; check relation registry and mapper branches.
- **Wrong actor/artifact:** inspect **external_reference** and **mapping_event** for that resource’s xref id.

---

## Related documents

- `DOCS/strategy/step-3-canonical-ontology-implementation-spec.md` — ontology and schema intent.
- `DOCS/strategy/step-3-debug-monitoring-and-execution.md` — adjacent strategy notes for debug and execution.

---

## Code references (for maintainers)

| Concern | Location |
|---------|----------|
| Debug routes | `backend/src/vector/api/http/routes/debug_canonical.py` |
| Response contracts | `backend/src/vector/contracts/debug_canonical.py` |
| Read queries (lists, detail, subgraph) | `backend/src/vector/infrastructure/db/repositories/canonical_debug_queries.py` |
| Canonical drain worker | `backend/src/vector/domains/canonical/worker.py` |
| GitHub mapping logic | `backend/src/vector/domains/canonical/github_mapper.py` |
| Sync chain (Step 2 + Step 3 after poll) | `backend/src/vector/api/http/routes/connectors/github.py` |

This document should remain **accurate** as those modules evolve; prefer updating this file when behavior or contracts change.
