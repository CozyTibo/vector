# Step 2 — Connector Projections: Implementation Plan

**Status:** Implemented in backend (`connector_projection_progress`, `github_*`, projection worker, `/debug/...` API + frontend debug page).  
**Scope:** Stage 2 only — `raw_ingestion_records` → GitHub **projection tables** (current state, UPSERT).  
**Depends on:** Step 1 ([step-1-v1-implementation-plan.md](./step-1-v1-implementation-plan.md), [step-1-ingestion.md](./step-1-ingestion.md)).

**Note:** `raw_ingestion_records.connector` already existed from Step 1 migration `20260330_0007`; migration `20260401_0009` adds the `(connection_id, connector, replay_sequence, id)` index plus projection tables.

**Out of scope:** cross-tool normalization, canonical entities (`Person`, …), execution graph, execution signals, tombstones/deletion reconciliation (accepted V1 gaps).

---

## 1. Purpose and constraints

### 1.1 What Step 2 delivers

- **Input:** Append-only rows in `raw_ingestion_records` for a GitHub connection, ordered by **`replay_sequence ASC, id ASC`**.
- **Output:** Durable, **query-friendly** tables holding the **latest observed** GitHub-native state per entity, keyed by **`(tenant_id, connection_id, …)`** natural keys.
- **Semantics:** Projections are **connector-shaped truth as Vector last saw it**, not authoritative GitHub truth and not canonical product truth.

### 1.2 Hard constraints (final)

| Constraint | Rule |
|------------|------|
| Raw store | **Append-only**; projections **never** mutate `raw_ingestion_records`. |
| Projection state | **Current snapshot** per entity; **UPSERT** only. |
| Ordering | All consumption **`ORDER BY replay_sequence ASC, id ASC`**. |
| Progress | Cursor **`(last_replay_sequence, last_id)`**; **backlog-driven**, not `run_id`-scoped. |
| Success filter | Process only rows where **`http_status`** indicates HTTP success (**2xx**; **default: 200** if ingestion only stores 200). |
| Concurrency | At most **one active projection worker** per **`(connection_id, connector)`**. |
| Cross projection FKs | **None**; soft references (`repository_github_id`, `author_github_id`, …). |
| Users | **`github_users`** row **only if payload provides numeric `github_id`** for the user object. |

### 1.3 Connector-agnostic architecture

Implement GitHub first, but:

- Name modules and the **progress/lock** table for **`connector`** (e.g. `'github'`), not hard-coded-only globals.
- **Router** maps `resource_type` → handler (`github.repository` → repository projector, …).
- Future connectors add their own projection tables and handlers; **same progress table shape** and **same cursor semantics** (per `(connection_id, connector)`).

---

## 2. Progress and locking (`connector_projection_progress`)

Single table for cursor + optional lease metadata (avoids a second table in V1).

### 2.1 Table: `connector_projection_progress`

| Column | Type | Nullable | Notes |
|--------|------|----------|--------|
| `connection_id` | `UUID` | NO | Part of PK. |
| `connector` | `VARCHAR(32)` | NO | e.g. `'github'`. Part of PK. |
| `tenant_id` | `UUID` | NO | Denormalized for tenant-scoped ops; must match the tenant owning `connection_id` (enforced in app). |
| `last_replay_sequence` | `BIGINT` | NO | Cursor component A. |
| `last_id` | `BIGINT` | NO | Cursor component B (`raw_ingestion_records.id`). |
| `lock_owner` | `VARCHAR(128)` | YES | Worker instance identifier (hostname + pid + uuid, etc.). |
| `lock_expires_at` | `TIMESTAMPTZ` | YES | Lease expiry; `NULL` when unlocked. |
| `updated_at` | `TIMESTAMPTZ` | NO | Last successful batch commit or lock heartbeat. |

**Primary key:** `(connection_id, connector)`

**Indexes:**

- `(tenant_id, connection_id, connector)` — ops/dashboards by tenant.

### 2.2 Cursor semantics

- **Lexicographic “strictly after”:** A raw row `(rs, rid)` is **unprocessed** iff  
  `(rs > last_replay_sequence) OR (rs = last_replay_sequence AND rid > last_id)`.
- **Initial state** for a new connection: insert row with **`last_replay_sequence = 0`**, **`last_id = 0`** (sentinel below all real `replay_sequence` / `id` values produced by Step 1).

### 2.3 Transaction rule (mandatory)

Within one DB transaction:

1. Acquire or verify lease (if using row-based locking — §8).
2. **SELECT** next batch of raw rows (§5).
3. **UPSERT** all derived projection changes for that batch.
4. **UPDATE** `last_replay_sequence`, `last_id` to the largest `(replay_sequence, id)` processed in the batch (lexicographic max).
5. Commit.

If the transaction aborts, the cursor does not advance; batch is retried. **UPSERT + merge rules must make reprocessing safe.**

---

## 3. Projection table schemas (GitHub V1)

Types use PostgreSQL conventions. **PKs are exactly as finalized.**

Common columns on **every** projection table:

| Column | Type | Notes |
|--------|------|--------|
| `tenant_id` | `UUID` NOT NULL | Indexed; tenant-scoped listings. |
| `connection_id` | `UUID` NOT NULL | Part of PK (except where PK is defined across connection + entity id). |
| `last_raw_record_id` | `BIGINT` NOT NULL | `raw_ingestion_records.id` that last contributed (provenance). |
| `last_observed_at` | `TIMESTAMPTZ` NOT NULL | **Ingestion observation time** = `raw_ingestion_records.fetched_at` of that raw row (not GitHub “updated” clock). |

Optional (recommended for debugging, not required by final decisions): add **`last_replay_sequence`** mirroring the raw row’s `replay_sequence` on projections — helps explain ordering without joining raw. Omit if you want minimal schema.

### 3.1 `github_repositories`

**Primary key:** `(connection_id, repository_github_id)`

| Column | Type | Nullable | Source / notes |
|--------|------|----------|----------------|
| `repository_github_id` | `BIGINT` | NO | `payload.id` |
| `node_id` | `TEXT` | YES | `payload.node_id` |
| `name` | `TEXT` | YES | |
| `full_name` | `TEXT` | YES | Lowercased for consistency optional; store as API gives unless product needs norm. |
| `owner_login` | `TEXT` | YES | `payload.owner.login` |
| `owner_github_id` | `BIGINT` | YES | `payload.owner.id` |
| `private` | `BOOLEAN` | YES | |
| `description` | `TEXT` | YES | |
| `default_branch` | `TEXT` | YES | |
| `html_url` | `TEXT` | YES | |
| `archived` | `BOOLEAN` | YES | |
| `disabled` | `BOOLEAN` | YES | |
| `fork` | `BOOLEAN` | YES | |
| `pushed_at` | `TIMESTAMPTZ` | YES | |
| `github_created_at` | `TIMESTAMPTZ` | YES | `payload.created_at` |
| `github_updated_at` | `TIMESTAMPTZ` | YES | `payload.updated_at` |

**Resource types:** `github.repository`  
**UPSERT key:** PK.

---

### 3.2 `github_pull_requests`

**Primary key:** `(connection_id, repository_github_id, pr_number)`

| Column | Type | Nullable | Source / notes |
|--------|------|----------|----------------|
| `repository_github_id` | `BIGINT` | NO | From `payload.base.repo.id` **or** parse consistency with repo context; prefer nested `base.repo.id`. |
| `pr_number` | `INT` | NO | `payload.number` |
| `pull_request_github_id` | `BIGINT` | YES | `payload.id` (global); useful for future APIs. |
| `node_id` | `TEXT` | YES | |
| `title` | `TEXT` | YES | |
| `body` | `TEXT` | YES | Optional; large text — OK for V1. |
| `state` | `TEXT` | YES | `open` / `closed` |
| `draft` | `BOOLEAN` | YES | |
| `author_github_id` | `BIGINT` | YES | `payload.user.id` |
| `author_login` | `TEXT` | YES | Denormalized convenience |
| `head_sha` | `TEXT` | YES | `payload.head.sha` |
| `head_ref` | `TEXT` | YES | `payload.head.ref` |
| `base_sha` | `TEXT` | YES | `payload.base.sha` |
| `base_ref` | `TEXT` | YES | `payload.base.ref` |
| `html_url` | `TEXT` | YES | |
| `merged_at` | `TIMESTAMPTZ` | YES | |
| `closed_at` | `TIMESTAMPTZ` | YES | |
| `github_created_at` | `TIMESTAMPTZ` | YES | |
| `github_updated_at` | `TIMESTAMPTZ` | YES | |

Also store **`repo_full_name`** (`TEXT`, YES) from `payload.base.repo.full_name` for human queries without joining repos.

**Resource types:** `github.pull_request`  
**UPSERT key:** PK.

**Implementation note:** If `repository_github_id` is missing from payload, **skip projection for that raw row** (log metric/warning) — do not invent keys.

---

### 3.3 `github_issues`

**Primary key:** `(connection_id, repository_github_id, issue_number)`

| Column | Type | Nullable | Source / notes |
|--------|------|----------|----------------|
| `repository_github_id` | `BIGINT` | NO | Same rule as PRs (`repository.id` on issue payload). |
| `issue_number` | `INT` | NO | `payload.number` |
| `issue_github_id` | `BIGINT` | YES | `payload.id` |
| `node_id` | `TEXT` | YES | |
| `title` | `TEXT` | YES | |
| `body` | `TEXT` | YES | |
| `state` | `TEXT` | YES | `open` / `closed` |
| `author_github_id` | `BIGINT` | YES | |
| `author_login` | `TEXT` | YES | |
| `html_url` | `TEXT` | YES | |
| `locked` | `BOOLEAN` | YES | |
| `github_created_at` | `TIMESTAMPTZ` | YES | |
| `github_updated_at` | `TIMESTAMPTZ` | YES | |
| `closed_at` | `TIMESTAMPTZ` | YES | |
| `repo_full_name` | `TEXT` | YES | |

**Resource types:** `github.issue`  
**UPSERT key:** PK.

Step 1 skips pull-request-shaped issues (`pull_request` key on payload); projector should **ignore** PR-masquerading issues if any slip through.

---

### 3.4 `github_commits`

**Primary key:** `(connection_id, repository_github_id, commit_sha)`

| Column | Type | Nullable | Source / notes |
|--------|------|----------|----------------|
| `repository_github_id` | `BIGINT` | NO | Derive from **ingestion context**: list-commits responses include limited repo info — use URL or parent listing context. Prefer **`raw.external_id`** parsing **only inside the worker** to recover `full_name`, then resolve `repository_github_id` from existing `github_repositories` row; if unknown, **skip or upsert repo first** when same batch contains repo observation. **Do not** expose parsing to downstream — store resolved `repository_github_id` on row. |
| `commit_sha` | `TEXT` | NO | `payload.sha`; 40-char hex |
| `message` | `TEXT` | YES | Commit message |
| `author_name` | `TEXT` | YES | |
| `author_email` | `TEXT` | YES | |
| `author_date` | `TIMESTAMPTZ` | YES | From `payload.commit.author.date` |
| `committer_name` | `TEXT` | YES | |
| `committer_email` | `TEXT` | YES | |
| `committer_date` | `TIMESTAMPTZ` | YES | |
| `author_github_id` | `BIGINT` | YES | When GitHub exposes user on commit wrapper |
| `committer_github_id` | `BIGINT` | YES | |
| `html_url` | `TEXT` | YES | |
| `parents_json` | `JSONB` | YES | Array of parent SHAs if present |

**Resource types:** `github.commit`

**Repository resolution (required impl detail):** List-commit payloads in Step 1 may not include numeric repo `id`. Final decision still requires **`repository_github_id` on PK**. Worker must:

1. Map commit → repo via **stable ingestion rule** (e.g. `external_id` format `owner/repo@sha` from Step 1 — verify in `github_poll_sync.py`).
2. Look up **`github_repositories.repository_github_id`** by `(connection_id, full_name)` **or** require repo rows processed earlier in same replay order (repositories should appear before per-repo commits in a naive full sync; if not guaranteed, **second pass** or **deferred commit rows** queue *out of scope* — prefer ensuring repo projections exist: ingestion order already iterates repos then commits).

Verify Step 1 `external_id` for commits: `f"{ref.full_name}@{h}"` — worker splits `full_name`, loads `repository_github_id` from `github_repositories` by `(connection_id, full_name)`. If repo row missing, **skip commit row** and increment **lag metric** (repo not yet projected).

---

### 3.5 `github_users`

**Primary key:** `(connection_id, github_id)`

| Column | Type | Nullable | Notes |
|--------|------|----------|--------|
| `github_id` | `BIGINT` | NO | From `user.id` |
| `login` | `TEXT` | YES | |
| `type` | `TEXT` | YES | `User`, `Organization`, `Bot`, … |
| `avatar_url` | `TEXT` | YES | |
| `html_url` | `TEXT` | YES | |
| `name` | `TEXT` | YES | If ever present |
| `bio` | `TEXT` | YES | Rare in short payloads — OK nullable |
| `site_admin` | `BOOLEAN` | YES | |

Plus standard: `tenant_id`, `connection_id`, `last_raw_record_id`, `last_observed_at`.

**Rule:** If `github_id` absent → **do not** insert/update `github_users` for that snippet.

---

## 4. UPSERT and merge rules (all entities)

### 4.1 Mechanism

Use PostgreSQL **`INSERT … ON CONFLICT (…) DO UPDATE`** (one statement per table affected per raw row, or batched with CTEs — implementation detail).

### 4.2 Partial payload merge (final)

For **every updatable scalar column** `c` (excluding PK, `tenant_id`, `connection_id` if immutable on row):

\[
c_{\text{new}} = \text{COALESCE}(c_{\text{from payload}}, c_{\text{existing}})
\]

**Meaning:** incoming **`NULL`** (missing or explicit null in extraction) **must not clobber** a non-null stored value.

**Exception columns** (always overwrite from payload when present — non-null incoming wins):

- `last_raw_record_id`
- `last_observed_at`

Use **Greatest** or conditional:  
`last_raw_record_id = EXCLUDED.last_raw_record_id` **if** this raw row is being applied **as the final update in the batch** for that entity — simpler rule: **always set** `last_*` from **this** raw row on conflict (last writer in batch wins; batch ordered by replay so **last raw row in batch for same entity** must be applied **last** within the SQL batch).

**Batch rule:** Process raw rows **in order** within a transaction. If two rows in the same batch touch the same PK, **later row wins** for non-COALESCE fields (`last_raw_record_id`, `last_observed_at`); for COALESCE fields, apply merge **sequentially** (row-by-row) **or** use a single SQL `UPDATE` chain — **row-by-row within batch** is simplest for correctness.

### 4.3 `tenant_id`

On insert: from raw row’s `tenant_id`. On conflict: **keep existing** `tenant_id` (should match); if mismatch, log fatal invariant break.

---

## 5. Projection worker architecture

### 5.1 Components

| Component | Responsibility |
|-----------|------------------|
| **Trigger** | After **successful** GitHub ingestion for `connection_id`, enqueue “drain projections” (async job, in-process hook, or cron). **No dependency on `run_id`.** |
| **Lock** | Ensure single worker per `(connection_id, 'github')` (§8). |
| **Fetcher** | Read `connector_projection_progress`, load batch from `raw_ingestion_records`. |
| **Router** | `resource_type` → handler. |
| **Handlers** | Parse JSON, extract typed fields, emit UPSERT statements + user side-effects. |
| **Commiter** | Single transaction: UPSERTs + cursor advance. |

### 5.2 Batch processing algorithm

**Parameters:** `BATCH_SIZE` (e.g. 500–2000), `connector = 'github'`, `HTTP_OK` filter (e.g. `http_status = 200`).

```
1. Begin transaction.
2. Lock lease for (connection_id, connector) — §8.
3. Read cursor (last_rs, last_id).
4. SELECT * FROM raw_ingestion_records
   WHERE connection_id = :conn
     AND connector = 'github'              -- if column exists on raw; else infer from resource_type prefix
     AND http_status BETWEEN 200 AND 299   -- or = 200 per product
     AND (replay_sequence > :last_rs
          OR (replay_sequence = :last_rs AND id > :last_id))
   ORDER BY replay_sequence ASC, id ASC
   LIMIT :BATCH_SIZE
   FOR UPDATE SKIP LOCKED   -- optional if multiple readers; usually single worker skips this
5. If empty → commit, release lease, exit.
6. For each row in order:
   6.1 Route by resource_type.
   6.2 Handler extracts fields; may upsert github_users from nested user objects (github_id required).
   6.3 Apply UPSERT to primary entity table with merge rules §4.
7. Set (last_rs, last_id) = (replay_sequence, id) of **last row** in batch.
8. UPDATE connector_projection_progress SET ... + lease heartbeat.
9. Commit.
10. If batch was full, loop (new transaction) until backlog drained or time budget.
```

**Note:** If `raw_ingestion_records` has **`connector`** column — use it; if not, treat `resource_type LIKE 'github.%'` as GitHub rows (Step 1 already uses `github.*` types).

### 5.3 Handler → table mapping

| `resource_type` | Primary table(s) | Side effects |
|-----------------|-----------------|--------------|
| `github.repository` | `github_repositories` | Upsert `github_users` for `owner` if `owner.id` present |
| `github.pull_request` | `github_pull_requests` | `user`, optional assignees (`github_id` only) |
| `github.issue` | `github_issues` | Same |
| `github.commit` | `github_commits` | Commit author/committer user objects if ids present |

---

## 6. Replay safety guarantees

| Property | Guarantee |
|----------|-----------|
| Deterministic order | Same raw total order → same sequence of merges **if** handlers are pure functions of payload + prior DB state. |
| At-least-once delivery | Crash after UPSERT, before commit → batch retries; **COALESCE** + ordered in-batch updates → stable. |
| At-most-once cursor | Cursor moves only on commit **after** full batch processed. |
| No raw mutation | Projections only read raw rows. |
| Idempotent replay | Re-running entire history from cursor `(0,0)` converges to same final projection state **for the same merge rules** (minus intentional non-monotonic edge cases accepted in V1). |

**Known non-guarantee:** Deleted GitHub entities remain in projections until manual rebuild or future tombstone stage — **accepted**.

---

## 7. `github_users` — detailed rules

1. **Insert/update only when** `user.id` (numeric) is present on the GitHub user object.
2. **Never create** user from **login-only** objects.
3. **Merge** profile fields with **`COALESCE(incoming, existing)`** per §4.2.
4. **`last_raw_record_id` / `last_observed_at`:** always updated when user row is touched by **that** raw record (even if no profile field changed — optional optimization: skip write if noop).
5. **Bots / orgs:** store `type` as given; do not coerce to canonical person.

---

## 8. Worker concurrency and locking

**Goal:** Max **one** active worker per `(connection_id, connector)`.

**Recommended pattern (V1):** **Lease column** on `connector_projection_progress`:

- **Acquire:** `UPDATE … SET lock_owner = :me, lock_expires_at = now() + interval '5 minutes' WHERE connection_id = ? AND connector = ? AND (lock_expires_at IS NULL OR lock_expires_at < now()) RETURNING *`.
- **Heartbeat:** refresh `lock_expires_at` each batch inside same transaction or periodic `UPDATE`.
- **Release:** `SET lock_owner = NULL, lock_expires_at = NULL` on normal exit; on crash, lease expires and another worker acquires.

**Alternatives:** `pg_try_advisory_lock(hashtext(connection_id::text || connector))` for process-local workers — also fine; document lock key scheme.

**Do not** shard the same connection across workers without application-level partition keys — not needed in V1.

---

## 9. Indexing strategy

### 9.1 Projection tables

**Every table:**

- PK as defined.
- **`(tenant_id, connection_id)`** — tenant listing.
- **`(tenant_id, connection_id, github_updated_at DESC NULLS LAST)`** (or `last_observed_at`) — optional “recent activity” **if** product needs it.

**`github_pull_requests`:**

- `(tenant_id, connection_id, state)` — open PR views.
- `(tenant_id, connection_id, repository_github_id)` — PRs by repo.

**`github_issues`:** analogous.

**`github_commits`:**

- `(tenant_id, connection_id, repository_github_id)` — commits per repo.

**`github_users`:**

- `(tenant_id, connection_id, login)` — **non-unique** lookup aid (login can theoretically change; index is best-effort search only).

### 9.2 Raw table (read path)

Ensure supporting index for the worker query (if not already present):

- **`(connection_id, replay_sequence, id)`** or `(connection_id, id)` **plus** filter — PostgreSQL can use **`(connection_id, replay_sequence, id)`** btree for the backlog scan.

Add **`WHERE http_status`** as partial index optional:  
`(connection_id, replay_sequence, id) WHERE http_status = 200 AND connector = 'github'` **if** `connector` exists on raw.

---

## 10. Operational considerations

### 10.1 Triggering

- **Primary:** On **successful** completion of `POST /connectors/github/sync` (or equivalent orchestrator), schedule **one drain** for that `connection_id`.
- **Safety net:** Periodic cron **“drain all connections with lag”** to fix missed triggers.

### 10.2 Monitoring

Metrics (names illustrative):

- **`projection_lag_rows`** — count of raw rows `(rs, id) > cursor` for connection.
- **`projection_batch_duration_seconds`**
- **`projection_skipped_rows`** — payload missing required keys (e.g. `repository_github_id`).
- **`projection_lock_contention`** — failed lease acquires.

Alerts when lag grows monotonically or lock stuck beyond **2× lease TTL**.

### 10.3 Rebuild / repair

**Full rebuild for one connection:**

1. Stop worker (or accept it will race — prefer maintenance mode).
2. **TRUNCATE** `github_*` rows **WHERE connection_id = ?** OR **`DELETE`** (truncate faster).
3. **Reset cursor** to `(0, 0)` for that `(connection_id, 'github')`.
4. Resume worker — replays all raw history in order.

**Partial repair:** Rare; fix forward with new raw ingestion. Avoid editing projection rows by hand.

### 10.4 Migrations

- Add all `github_*` tables + `connector_projection_progress` in **Alembic** revision(s).
- **No FK** from projections to projections; **optional** FK from `last_raw_record_id` → `raw_ingestion_records(id)` — **product choice:** FK helps integrity but prevents pruning old raw rows; for V1 **omit FK** if retention might delete raw later.

---

## 11. Testing plan (acceptance)

| Test | Intent |
|------|--------|
| Unit: merge helper | `COALESCE` behavior for partial payloads. |
| Unit: handlers | Golden JSON fixtures per `resource_type` → expected upsert dicts. |
| Integration: worker batch | Insert N raw rows out of order IDs but correct `replay_sequence`; verify final projection matches sequential application. |
| Integration: cursor | Crash mid-batch (abort txn) → cursor unchanged; retry converges. |
| Integration: concurrency | Two workers; only one acquires lease / makes progress. |
| Integration: user skip | Login-only payload → no `github_users` row. |
| Integration: http filter | 4xx/5xx raw rows **skipped** for projections. |

---

## 12. Deliverables checklist

- [ ] Alembic migration(s): `connector_projection_progress` + five `github_*` tables + indexes.
- [ ] Domain package: `vector.domains.projections.github` (or similar): router, handlers, merge/UPSERT builders.
- [ ] Worker entrypoint: drain function `drain_github_projections(session, connection_id, batch_size=...)`.
- [ ] Trigger wiring after successful GitHub ingestion.
- [ ] Metrics / structured logs (`connection_id`, `tenant_id`, batch size, new cursor).
- [ ] Documentation link from README / internal runbook (ops §10).

---

## 13. Future connectors (non-blocking)

Adding **Linear**, **Slack**, etc.:

1. New `resource_type` prefixes and projection tables (`linear_*`, …).
2. Same **`connector_projection_progress`** row with `connector = 'linear'`.
3. Same ordering contract **if** Stage 1 stores **`replay_sequence` + `id`** globally (already true).
4. Separate handler modules; shared worker loop parameterized by `connector`.

---

**Document version:** 1.0  
**Last updated:** Aligned with finalized Step 2 architecture decisions (ordering, cursor, natural keys, users, merge rules, tenant_id, no inter-projection FKs).
