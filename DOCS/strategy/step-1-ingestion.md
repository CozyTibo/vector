# Step 1 — Ingestion Layer Design Document

**Status:** Draft for review  
**Scope:** Stage 1 only — reliable API retrieval + durable ingestion envelopes (polling first; webhook-ready)  
**Out of scope:** Connector projections (Stage 3), canonical entities (Stage 4), execution graph, business event inference, deletion/tombstones (explicitly deferred per v1 policy)

**V1 implementation:** See [step-1-v1-implementation-plan.md](./step-1-v1-implementation-plan.md) for the concrete GitHub-first plan (minimal envelope, three tables, resource-level records).

---

## Philosophy check

**The Step 1 philosophy is sound** for a multi-connector execution intelligence platform: **append-only retrieval observations**, rich **lineage metadata**, **no normalization**, and a **unified envelope** that can later absorb webhooks matches how serious data platforms survive API drift and replay.

**Major architectural risks to keep visible (not blockers):**

1. **“Non-interpretive” has limits** — Choosing endpoints, expansions, pagination, and filters is already a *retrieval contract*. The mitigation is documenting and storing that contract in metadata so replay is honest.
2. **V1 deletion silence** — Acceptable *if explicit* (as written below). The risk is downstream teams assuming “if it’s not ingested, it doesn’t exist” without reconciliation. Keep that boundary loud in docs and ops.
3. **Incremental correctness vs cost** — Incremental polling can miss edge cases; most systems pair incrementals with periodic reconciliation later. Say so upfront to avoid false confidence.
4. **Volume/retention** — Append-only grows fast (later: Slack). Step 1 should assume **retention/classification** will become connector-aware even if GitHub v1 is simple.

---

## System architecture (four stages)

This system is an execution intelligence platform that ingests data from multiple tools (GitHub, Jira, Slack, CI/CD, etc.) and eventually builds a unified execution graph.

The pipeline is intentionally separated into four stages:

1. **Ingest (connector fetch layer)** — *this document*
2. **Raw storage (append-only snapshots of external data)** — may be the same physical store Step 1 writes to
3. **Connector projections (tool-specific state tables)**
4. **Canonical normalization (tool-independent entities)**

Later stages will feed an execution graph that powers signals, initiative detection, and prediction.

---

## 1. Purpose and boundaries

### 1.1 What Step 1 delivers

Step 1 produces **append-only ingestion records** (“retrieval observations”) that answer:

- **What** was fetched (connector + resource identity + payload)
- **When** it was fetched (ingestion time + optional wire timestamps)
- **How** it was fetched (endpoint, parameters, pagination/cursor context, HTTP outcome)
- **Where** it came from (tenant + connection/account/installation context)

### 1.2 What Step 1 must not do

- No canonical identity resolution (no “this GitHub user equals this Person”)
- No cross-tool joins or graph edges
- No business event detection (“PR merged event”) — that is projection/normalization/analytics territory
- No overwriting prior snapshots (append-only)

### 1.3 Relationship to later stages

- **Stage 2 (raw storage)** can be **the same physical table** as Step 1 writes, as long as it remains append-only and auditable.
- Stages 3–4 consume these records as **inputs** and may **replay** transformations without requiring refetch (unless payloads are incomplete by retrieval design).

---

## 2. Components of the ingestion layer

### 2.1 Connector adapter (per vendor: GitHub first)

**Responsibilities**

- Acquire and refresh credentials appropriate to the connection (tokens, GitHub App auth — details live in connector implementation)
- Construct requests for a defined **retrieval contract** (which endpoints, which fields/expansions, pagination strategy)
- Translate vendor errors into a small internal taxonomy (`TRANSIENT`, `RATE_LIMITED`, `AUTH`, `CLIENT_ERROR`, `SERVER_ERROR`, `UNKNOWN`)
- Emit **normalized-for-ingestion-only** request descriptors (method, path template, query params) + raw response body

**Non-responsibilities**

- Mapping into canonical entities
- Writing projections

### 2.2 Fetch executor (shared runtime)

**Responsibilities**

- Timeouts, connection pooling, bounded concurrency
- Retries with jitter; honor `Retry-After` when present
- Centralized logging/metrics hooks (per run, per connection)
- Optional request signing / header injection policies per connector

### 2.3 Run orchestrator (“sync runner”)

**Responsibilities**

- Create an `ingestion_run` record at start; finalize with status
- Drive a connector-defined **sync plan** (phases), e.g. repositories → PRs/issues → commits (exact plan is GitHub-specific, orchestration pattern is generic)
- Persist progress via **checkpoints** so partial failures are resumable
- Ensure **idempotent writes** to raw records on retries (same logical fetch should not create unbounded duplicates)

### 2.4 Cursor / checkpoint store (`connector_sync_state`)

**Responsibilities**

- Durable progress for large traversals (“repo list page 7”, “PR list since cursor X for repo R”)
- Opaque blobs interpreted only by the owning connector

### 2.5 Raw record writer

**Responsibilities**

- Persist append-only ingestion envelopes (see §4)
- Compute payload hash/checksum
- Associate each envelope with `run_id`, `connection_id`, `tenant_id`

### 2.6 Observability and operations (minimum viable)

- Structured logs: `run_id`, `connection_id`, connector, phase, resource_type, latency, outcome
- Metrics: counts of records written, 429 rate, error rate, run duration, retries
- **Failure visibility:** V1 uses `ingestion_runs.error_summary` only (no separate run error table); structured logs for detail.

---

## 3. Minimal database schema (conceptual)

This is the smallest set that supports durable Step 1 ingestion with polling, checkpointing, monitoring, and future webhook parity.

### 3.1 `ingestion_runs`

**Purpose:** One row per execution of ingestion for a connection (recommended **per connection** for v1).

**Recommended fields (conceptual)**

- `id` (uuid)
- `tenant_id`
- `connection_id`
- `connector` (enum/text: `github`, …)
- `source_trigger` (`poll` in v1; future: `webhook`, `replay`, `backfill`)
- `status` (`running`, `succeeded`, `failed`, `cancelled`, optionally `partial`)
- `started_at`, `finished_at`
- `error_summary` (short, operator-facing)
- `stats` (json/jsonb optional: pages fetched, records written, etc.)

**Notes**

- `partial` is valuable if checkpointing resumes without pretending full success.

### 3.2 `raw_ingestion_records` (append-only)

**Purpose:** Durable store of retrieval observations (payload + envelope metadata).

**Constraints**

- Append-only (no updates/deletes in normal operation)
- Heavy indexing deferred except what you need for ops/debug/replay

### 3.3 `connector_sync_state`

**Purpose:** Opaque checkpoint state for incremental/paginated polling.

**Keying (recommended)**

- `(tenant_id, connection_id, connector, scope_key)`  
  where `scope_key` is connector-defined (e.g. `github:repo_list`, `github:prs:org/repo`)

**Fields**

- `cursor` / `state` (json/jsonb blob)
- `updated_at`
- optional `last_successful_run_id`

### 3.4 V1 simplifications (confirmed)

- **No** separate `ingestion_run_errors` or `ingestion_idempotency_keys` tables; run-level errors live in `ingestion_runs.error_summary` only.
- **`idempotency_key`** on `raw_ingestion_records` (V1: always populated; `UNIQUE(run_id, idempotency_key)`), not a separate table.

---

## 4. Ingestion envelope structure (`raw_ingestion_records`)

**Granularity (V1):** one row represents **one resource** after unpacking list responses (not one row per HTTP page).

**Resource typing:** namespaced `resource_type` values (e.g. `github.repository`, `github.pull_request`, `github.issue`, `github.commit`) so future connectors can add `jira.issue`, `linear.issue`, etc. without collisions.

### 4.1 V1 minimal envelope (columns only)

Store **only** the fields below in V1; avoid extra columns (vendor request ids, header snapshots, byte counts, correlation ids, etc.) unless a later version proves they’re necessary.

- **Tenancy & identity:** `tenant_id`, `connection_id`, `connector`, `resource_type`, `external_id`
- **Retrieval contract:** `api_endpoint` (logical template, no secrets), `query_params` (json)
- **Payload:** `payload_body` (json), `payload_hash`
- **Wire:** `http_status`, `fetched_at`
- **Provenance:** `run_id`, `source_trigger` (`poll` in V1; reserve `webhook`, `replay`, `backfill`)
- **Replay order:** `replay_sequence` (bigint from DB sequence) + row `id` — consumers replay in **`ORDER BY replay_sequence ASC, id ASC`** (see `vector.domains.ingestion.replay_ordering`).
- **Dedupe:** `idempotency_key` (same table; V1 implementation always sets it, `UNIQUE(run_id, idempotency_key)`).

### 4.2 Explicit non-goals inside the envelope

- No canonical `Person`/`Task` fields
- No inferred events (`opened`, `merged`) — only raw payload as returned per resource

---

## 5. Incremental polling design

### 5.1 Two-track model (recommended)

1. **Checkpoints (mechanical progress):** resume scans safely (pagination, repo enumeration).
2. **Incremental filters (semantic freshness, vendor-specific):** reduce work when APIs support `since`, branch tips, conditional requests, etc.

**Rule:** incremental strategies live in the **GitHub connector**; the DB stores **opaque checkpoint blobs** + optional simple watermarks.

### 5.2 GitHub v1 guidance (illustrative, not binding implementation)

- **Repositories list:** checkpoint per page cursor / last processed repo identifier.
- **PRs/issues:** prefer API-supported sorting/filtering if reliable; otherwise checkpoint within a repo’s list traversal.
- **Commits:** typically traverses SHAs/time ranges; checkpoint by ref + date/SHA cursor as supported.

### 5.3 Practical correctness stance

Polling ingestion should document:

- **best-effort incremental correctness**, and
- future **reconciliation** passes (Stage 3 operational behavior) for long-term hygiene — without requiring Step 1 to emit tombstones in v1.

---

## 6. Orchestration and monitoring

### 6.1 Run lifecycle

1. Create `ingestion_run` (`running`)
2. Load `connector_sync_state` for relevant scopes
3. Execute planned phases with checkpoint updates after safe points
4. Append `raw_ingestion_records` continuously (batched inserts acceptable)
5. Finalize run:
   - `succeeded` if all phases complete
   - `partial` if checkpointed and stopped safely (operator choice)
   - `failed` with **`error_summary`** on `ingestion_runs` (V1 has no per-phase error table)

### 6.2 Monitoring expectations

- Dashboards/alerts on: run failures, rising 429s, stalled runs, zero-record runs (often a signal of bad filters/tokens)
- Debug workflow: locate `run_id` → read `error_summary` + logs → sample `raw_ingestion_records` for that run

### 6.3 Rate limits and backoff

- Policy belongs in fetch executor; connector surfaces whether a failure is rate-limit-driven
- Persist enough metadata to distinguish “we got rate limited” from “resource missing”

---

## 7. Future compatibility (by design)

### 7.1 Webhooks

- Webhook receiver validates signature and enqueues work that creates an `ingestion_run` (or sub-run) with `source_trigger=webhook`
- Each delivery becomes one or more `raw_ingestion_records` using the **same envelope**; include webhook delivery id in `idempotency_key` / metadata json

### 7.2 Additional connectors

- New connector = new adapter + new `resource_type` taxonomy + connector-specific checkpoint `scope_key` conventions
- DB tables remain stable if envelope is generic

### 7.3 Replay for normalization

- Normalization jobs can reprocess `raw_ingestion_records` by:
  - `connection_id` + time window, or
  - `run_id`, or
  - `resource_type` + `external_id` history
- Payload hash helps detect accidental duplicate fetches vs true duplicates

### 7.4 Debugging ingestion failures

Minimum viable story:

- `ingestion_runs.error_summary` + structured **logs** (V1)
- envelope includes `api_endpoint`, `query_params`, `http_status`

---

## 8. V1 decisions explicitly accepted

- **No deletion/tombstone detection in Step 1** — if a resource disappears from the API, Step 1 stops observing it; deletion detection is deferred to reconciliation or projection logic.
- **Polling only execution path**, but envelope supports `source_trigger`
- **GitHub first** to validate generality of envelope + orchestration patterns (repositories, pull requests, issues, commits)

---

## 9. Open questions (before coding)

1. ~~**Granularity:**~~ **Resolved (V1):** one envelope per **resource**; unpack list pages.
2. **PII/redaction:** GitHub may be fine early; define a policy placeholder for Slack-like connectors.
3. **Retention:** not solved in V1 — **revisit before high-volume connectors** (e.g. Slack); see implementation plan §8.
