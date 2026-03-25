# Step 1 — V1 Implementation Plan (GitHub, polling)

**Status:** Ready for implementation  
**Scope:** Stage 1 only — connector fetch → append-only **resource-level** ingestion envelopes.  
**Companion doc:** [step-1-ingestion.md](./step-1-ingestion.md) (architecture and philosophy).

**Out of scope for V1:** projections (Stage 3), canonical normalization (Stage 4), webhooks (except envelope field `source_trigger`), tombstones/deletion detection, retention/TTL automation.

---

## Confirmed V1 product rules (summary)

| Topic | Decision |
|--------|-----------|
| Record granularity | **One row per resource** (unpack list pages into many rows). |
| Resource types | **Namespaced** (`github.repository`, `github.pull_request`, `github.issue`, `github.commit`). |
| Envelope | Shown in §3 — **minimal fields only**; no vendor request ids, header dumps, byte counts, etc. |
| Extra tables | **No** `ingestion_run_errors`, **no** `ingestion_idempotency_keys` table. Optional **`idempotency_key` column** on `raw_ingestion_records` only. Run failures → `ingestion_runs.error_summary`. |
| Deletions | **Not detected** in Step 1; resources that vanish from the API simply stop appearing. |
| Trigger | **Polling only**; set `source_trigger = poll` (values like `webhook` / `replay` / `backfill` reserved). |
| Retention | **Not implemented in V1.** Revisit before high-volume connectors (e.g. Slack). See §8. |

---

## 1. Runtime components to implement

Deliver these as **clear modules** (exact package names TBD in repo conventions).

### 1.1 GitHub connector adapter

- **Input:** `tenant_id`, `connection_id`, GitHub installation context (from `github_connection_details` / existing install model), `installation_id` for token exchange.
- **Output:** Iterator or small **fetch plan** steps: each step = HTTP descriptor + interpretation of response into **N resource payloads** (or async batch).
- **Responsibilities:**
  - Build GitHub REST **request descriptors** (method, path template, `query_params` dict).
  - Obtain **installation access token** (GitHub App) when needed; refresh per run or TTL-based (implementation detail).
  - Parse **pagination** (Link header `rel=next` and/or `page` / `per_page` per GitHub docs).
  - **Unpack** list responses into per-resource objects; each object becomes one envelope’s `payload_body`.
  - Map each resource to `resource_type` + `external_id` (see §4).
- **Non-responsibilities:** DB writes, canonical IDs, projections.

### 1.2 Fetch executor (shared)

- HTTP client with timeouts, optional connection pooling.
- **Retries:** transient errors + **429** with backoff; respect `Retry-After` when present.
- **Rate limiting:** conservative default concurrency (configurable); surface typed errors to orchestrator.
- **Logging:** structured logs with `run_id`, `connection_id`, phase, URL **path** (avoid logging secrets/tokens).

### 1.3 Run orchestrator (“GitHub sync runner”)

- Single entry point for “run ingestion for this `connection_id`”.
- **Lifecycle:** §5.
- Loads **checkpoints** from `connector_sync_state`, invokes connector + executor, calls **raw writer** in batches.
- On **fatal error:** set run `failed`, write **short** `error_summary` (and log stack/details).
- On **partial progress:** optional `partial` status + checkpoint so the next run can resume (recommended for large installs).

### 1.4 Raw record writer

- Given structured envelope fields (§3), compute **`payload_hash`**, insert into `raw_ingestion_records`.
- Batch inserts (e.g. hundreds per transaction) for throughput.
- **Retry dedupe:** if using `idempotency_key`, use **ON CONFLICT DO NOTHING** (or pre-check) so a **retried** HTTP fetch does not duplicate rows within the same logical work. *(If you prefer “no dedupe, accept duplicate rows on retry,” make that an explicit trade-off; default recommendation is dedupe on retry only via `idempotency_key`.)*

### 1.5 Checkpoint store (`connector_sync_state`)

- Thin repository: **get / upsert** JSON state by `(tenant_id, connection_id, connector, scope_key)`.
- **Scope keys** are GitHub-defined strings (§4.3); value is an **opaque JSON blob** interpreted only by the GitHub connector.

### 1.6 Trigger / worker wiring (minimum)

- **V1:** HTTP admin/task endpoint or CLI/cron hook that starts a run for a given `connection_id` (whatever matches the existing app).
- **Async:** queue or background task recommended so long polls do not block HTTP (implementation choice).

---

## 2. Minimal database schema (V1)

Three tables only.

### 2.1 `ingestion_runs`

| Column | Type | Notes |
|--------|------|--------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | Denormalized for easy filtering (matches connection’s tenant). |
| `connection_id` | UUID FK | `tenant_connections.id` (GitHub row). |
| `connector` | text | e.g. `github`. |
| `source_trigger` | text | V1: `poll`. |
| `status` | text | `running` / `succeeded` / `failed` / `partial` / `cancelled`. |
| `started_at` | timestamptz | |
| `finished_at` | timestamptz nullable | |
| `error_summary` | text nullable | Human-readable; **only** run-level error surface for V1. |
| `stats` | jsonb nullable | **Optional** small object e.g. `{"records_written": N}` — omit if you want strict minimalism. |

**Indexes (suggested):** `(connection_id, started_at DESC)`, `(tenant_id, started_at DESC)`.

### 2.2 `raw_ingestion_records` (append-only)

| Column | Type | Notes |
|--------|------|--------|
| `id` | bigserial PK | |
| `replay_sequence` | bigint NOT NULL | **Monotonic ingest order** — default `nextval('raw_ingestion_replay_seq')`. Consumers MUST replay in **`ORDER BY replay_sequence ASC, id ASC`** (see `vector.domains.ingestion.replay_ordering`). |
| `tenant_id` | UUID | |
| `connection_id` | UUID | |
| `connector` | text | |
| `resource_type` | text | e.g. `github.pull_request`. |
| `external_id` | text | Stable within connector + type (§4.2). |
| `api_endpoint` | text | Logical template, e.g. `GET /repos/{owner}/{repo}/pulls` or `GET /installation/repositories`. **Do not** store tokens. |
| `query_params` | jsonb | Dict; empty object if none. |
| `payload_body` | jsonb | Single resource JSON (object) as returned by API (or normalized sub-object). |
| `payload_hash` | text | Hash of canonical JSON encoding of `payload_body` (define one rule, e.g. `sha256` of UTF-8 JSON with sorted keys). |
| `http_status` | int | Typically 200 for successful resource materialization. |
| `fetched_at` | timestamptz | Server time when the row was written / observation recorded. |
| `run_id` | UUID FK | `ingestion_runs.id`. |
| `source_trigger` | text | Duplicate of run for replay-friendly exports; V1 `poll`. |
| `idempotency_key` | text NOT NULL | Hash of `(run_id, resource_type, external_id, api_endpoint, canonical query_params)` — unique per run with `(run_id, idempotency_key)` so executor retries do not duplicate rows. |

**Indexes (suggested):** `(run_id)`, `(connection_id, resource_type, fetched_at DESC)`, `(connection_id, external_id, fetched_at DESC)`, `(replay_sequence, id)` for replay scans.

**Uniqueness:** `UNIQUE(run_id, idempotency_key)`.

### 2.3 `connector_sync_state`

| Column | Type | Notes |
|--------|------|--------|
| `tenant_id` | UUID | |
| `connection_id` | UUID | |
| `connector` | text | `github`. |
| `scope_key` | text | e.g. `github:installation_repositories`, `github:pulls:owner/repo`. |
| `state` | jsonb | Opaque connector state (§4.3). |
| `updated_at` | timestamptz | |

**Primary key:** `(tenant_id, connection_id, connector, scope_key)`.

---

## 3. Minimal ingestion envelope (V1) — field mapping

Stored **only** as the columns in §2.2 (no extra envelope columns in V1).

- **`api_endpoint`:** stable **logical** name of the operation, not the full URL with query string (query string belongs in `query_params`).
- **`query_params`:** e.g. `{"state": "all", "sort": "updated", "direction": "desc", "per_page": 100, "page": 2}`.
- **`http_status`:** from the **HTTP call** that produced this resource (usually 200; if you ever materialize from a nested structure, still record the parent response status).
- **`payload_hash`:** enables cheap duplicate detection and integrity checks during replay.

---

## 4. GitHub ingestion strategy (V1)

**Assumptions:** GitHub **App** installation (already in schema: `installation_id`). Use **GitHub REST API v3** with appropriate `Accept` / API version header per your app’s chosen pinned version.

### 4.1 Resource identity (`external_id`)

| `resource_type` | `external_id` (V1 convention) |
|-----------------|--------------------------------|
| `github.repository` | `{owner}/{name}` (lowercase owner per GitHub normalization) |
| `github.pull_request` | `{owner}/{repo}#{number}` |
| `github.issue` | `{owner}/{repo}#{number}` (issues only; exclude PRs — see below) |
| `github.commit` | `{owner}/{repo}@{full_sha}` |

### 4.2 Endpoints (list → unpack to one record per element)

1. **Repositories (installation-scoped)**  
   - **Request:** `GET /installation/repositories` with pagination (`per_page`, `page` or Link header).  
   - **Records:** one `github.repository` per `repositories[]` item; `payload_body` = that repo object.

2. **Pull requests (per repo)**  
   - **Request:** `GET /repos/{owner}/{repo}/pulls` with `state=all`, `sort=updated`, `direction=desc`, pagination.  
   - **Records:** one `github.pull_request` per element in response array; `payload_body` = that PR object.  
   - **V1 payload note:** list items are usually sufficient; a follow-up iteration can add optional `GET /repos/{owner}/{repo}/pulls/{pull_number}` if you require maximum field completeness.

3. **Issues (per repo)**  
   - **Request:** `GET /repos/{owner}/{repo}/issues` with `state=all` and **`since`** when doing incremental (ISO 8601 from checkpoint). Pagination as documented.  
   - **Filter before write:** skip items that include a `pull_request` URL field — treat those as PRs, not `github.issue` (avoids duplicating PR coverage under issue type).  
   - **Records:** one `github.issue` per remaining item.

4. **Commits (per repo)**  
   - **Request:** `GET /repos/{owner}/{repo}/commits` on **default branch** first (`sha` = default branch name from repo object, stored in checkpoint or re-read from repo payload). Pagination; use `per_page` max allowed.  
   - **Incremental:** if checkpoint has `since` ISO timestamp, pass GitHub’s `since` query param where supported to reduce pages.  
   - **Records:** one `github.commit` per commit object in the response array; `external_id` uses **full** `sha`.

### 4.3 Pagination

- Follow GitHub’s documented approach: **`page` / `per_page`** and/or **Link header** `rel="next"` depending on endpoint.  
- Connector **does not normalize** pages into one DB row; orchestrator loops until no next page, writing **resource rows** after each page **or** buffering then flush (implementation choice).

### 4.4 Incremental sync (V1, pragmatic)

Use **`connector_sync_state`** for two mechanisms:

1. **Mechanical checkpoints:** resume mid-scan (e.g. repo N of M, PR page cursor).  
2. **Watermarks (where API supports):**
   - **Issues:** store `last_issues_since` / “last synced at” per repo in scope state; use `since` on the next run (GitHub returns issues **updated** at or after `since`).  
   - **Commits:** store `last_commit_since` per repo; pass `since` on list commits when resuming incremental.  
   - **Pull requests:** list endpoint has **no** `since` param — **V1 options:** (a) full scan each run with checkpoints only; or (b) **recommended:** sort `updated` desc and **stop early** when all PRs on the current page have `updated_at` older than stored watermark `last_pr_updated_at` (with overlap window, e.g. re-fetch last 1–2 pages for safety); update watermark after successful completion. Document that this is **best-effort** incremental.

**First run:** empty checkpoints → full traversal (still paginated).  
**Later runs:** reuse watermarks + checkpoints; **periodic full refresh** (e.g. weekly) can be a future ops toggle — not required for V1 code if you accept best-effort incremental.

### 4.5 Ordering of work in a run (suggested)

1. Ingest / refresh **repositories** for the installation (checkpoint at page level).  
2. For **each** repository (sequential per repo in V1 to limit fan-out, or bounded parallel with rate-limit awareness):  
   - pull requests → issues → commits (order is flexible; commits do not require PRs first).

### 4.6 Auth and errors

- Installation access token: request as needed, cache **in memory for the run** (do not persist token in `query_params` or envelope).  
- **401/403:** fail run with clear `error_summary`.  
- **404** on a repo that disappeared: skip or abort phase per policy (**V1:** log and skip that repo, continue others — aligns with “no tombstones”; resource simply stops being updated).

---

## 5. Ingestion run lifecycle

1. **Start:** Insert `ingestion_runs` with `status=running`, `source_trigger=poll`, `started_at=now()`, `connector=github`.  
2. **Load checkpoints:** Read all `connector_sync_state` rows for `(tenant_id, connection_id, github)` (or lazy-load per scope).  
3. **Fetch–write loop:** For each orchestration phase (repos → per-repo resources):  
   - Call executor → connector returns a page of resources.  
   - Map each to envelope fields; compute `payload_hash`; assign `idempotency_key` if used; **batch insert** `raw_ingestion_records`.  
   - **Update checkpoint** in `connector_sync_state` after durable insert (or after each safe page — choose **checkpoint after durable write**).  
4. **Finish:** Set ingest `status` `succeeded`, `finished_at=now()`; optionally `stats`.  
5. **On error:** `status=failed` (or `partial` if you intentionally support resume), `error_summary` set, `finished_at` set, **checkpoint** reflects last good progress.

**Monitoring V1:** rely on `ingestion_runs` + application logs; no separate error table.

---

## 6. Walkthrough — second GitHub poll for one installation

**Setup:** Tenant T has GitHub connection C with `installation_id` I. Prior run already populated checkpoints and watermarks.

1. Operator triggers **sync** for C.  
2. Orchestrator creates **run** R1 (`running`).  
3. **Repositories:** Fetches `GET /installation/repositories` page 1 → 80 repos; unpacks → **80** `raw_ingestion_records` with `resource_type=github.repository`. Checkpoint `github:installation_repositories` updated (`page=2` or next cursor).  
4. Page 2 → 20 repos → **20** rows; no next page → repo phase done; checkpoint cleared or marked complete.  
5. **Repo `acme/api` — PRs:** Fetches `GET /repos/acme/api/pulls?...&page=1`, unpacks 50 PRs → 50 rows (`github.pull_request`, ids like `acme/api#101`). Watermark not yet advanced mid-phase.  
6. Page 2 has PRs all with `updated_at` before watermark → **early stop** (if using incremental PR strategy); else continue until last page.  
7. **Issues:** `GET /repos/acme/api/issues?since=2025-01-01T00:00:00Z` → unpack non-PR issues → N rows.  
8. **Commits:** `GET /repos/acme/api/commits?sha=main&since=...` → unpack → M rows.  
9. Repeat 5–8 for other repos (may skip repos with unchanged watermarks if future optimization adds “skip repo” — not required V1).  
10. Run R1 → `succeeded`, `finished_at` set, `stats` e.g. total rows written **1,240**.  

**If** page 3 of PRs hits a **429**, executor backs off, retries; if DB insert had succeeded for pages 1–2, checkpoint is already past those pages — **retry must not duplicate** rows: `idempotency_key` + upsert or conflict ignore prevents duplicates for the same `run_id` / fetch attempt (define key to align with “per resource per attempt”).

---

## 7. Future-facing compatibility (no extra V1 scope)

- **Webhooks:** same tables; new runs with `source_trigger=webhook`; optionally derive `idempotency_key` from delivery id later.  
- **More connectors:** same schema; new `connector` value and `jira.*` resource types.  
- **Normalization replay:** consumers query `raw_ingestion_records` by time, `run_id`, or `external_id` history.  
- **Debugging:** filter by `run_id`; inspect `error_summary`; compare `payload_hash` across runs for same `external_id`.

---

## 8. Retention reminder (no implementation in V1)

Append-only storage will grow with every poll and every resource. **V1 does not implement retention, archival, or TTL.**

Before ingesting **high-volume** connectors (e.g. **Slack** or other chat/collab tools), revisit:

- per-connector **retention** / **sampling** policy,  
- whether **raw** stays row-per-message or moves large blobs to object storage,  
- **legal/PII** constraints.

Document outcomes in strategy docs when those connectors start.

---

## 9. Testing strategy (V1)

### Goals

- **Unit:** fast, no DB — pure helpers and small behaviors.
- **Integration:** HTTP + DB (`make test`), optional GitHub mocked at the process boundary.
- **E2E / contract:** optional later — real GitHub App against a throwaway org (manual or nightly); not required for CI in V1.

### What exists today

| Layer | Coverage |
|--------|-----------|
| **Unit** | `tests/vector/domains/ingestion/test_payload.py` — canonical JSON hash, idempotency key stability. |
| **Integration** | `tests/vector/api/http/test_github_sync_integration.py` — `POST /connectors/github/sync`: 401 unauthenticated; 400 when GitHub not connected; 200 when `run_github_poll_ingestion_for_tenant` is stubbed (avoids live GitHub in CI). |
| **Not yet (optional next)** | Repository tests for `insert_raw_records_ignore_conflict` + replay ordering query; `FetchExecutor` retry behavior with `respx`/`httpx`; full sync with `httpx` mocks matching GitHub pagination JSON. |

### Conventions

- Mark DB-backed tests with `@pytest.mark.integration` (skipped when `DATABASE_URL` unset unless using `make test`).
- Patch at the **route boundary** (`vector.api.http.routes.connectors.github`) when testing HTTP without calling GitHub.
- For “real” sync tests locally, call `POST /connectors/github/sync` with a dev tenant that has a GitHub installation and valid `GITHUB_APP_*` — expect long runtime; keep out of default CI.
