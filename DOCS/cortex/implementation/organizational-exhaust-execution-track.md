# Organizational Exhaust — Gap Map & Execution Roadmap (Phase 01)

**Normative spec:** `../01-ingestion/phase-01-organizational-exhaust-spec.md`  
**Continuity (modes, idempotency, live/replay, convergence):** `../01-ingestion/phase-01-ingestion-continuity-doctrine.md`  
**Live-lane idempotency lock:** `../01-ingestion/phase-01-live-idempotency-doctrine.md`  
**Tracker steps:** `../MASTER_TRACKER.md` Phase 01 **Steps 7–16** (Step **16** = final runtime-correctness exit gate; Steps 0–6 = substrate only).  
**Short definition:** `../01-ingestion/real-ingestion-definition.md`  
**Matrix + registry:** `../connectors/connector-exhaust-matrix.md`, `backend/.../exhaust_coverage_registry.py`  
**Code pointers:** `sync_executor.py`, `connectors/*/ingestion_api.py`, `connectors/github/http_client.py`, `checkpoint_contract.py`, `settings.py`

**Roadmap ↔ tracker:** R0 → **Step 7**; R1 → **Step 8**; R2 → **Step 9**; R3 → **Step 10**; R4 → **Step 11**; R5 → **Step 12**; R6 → **Step 13**; R7 → **Step 14**; R8 → **Step 15**; R9 → **Step 16**.

This document is **implementation-facing**: gap truth, roadmap steps, risks, open decisions. It replaces vague “expansion” language with **concrete streams and APIs**.

---

## A. Sequencing rationale (why this order)

1. **Slack + GitHub first** — highest volume of organizational narrative + delivery evidence; most product reconstruction drills depend on them.
2. **Linear next** — issue evolution GraphQL; depends on stable cursor/id patterns similar to GitHub.
3. **Notion** — large block trees; needs crawl + cursor discipline; often rate-limited.
4. **Calls** — provider-specific; blocked on **which** API (Meet, Zoom, etc.) and legal retention; parallel track once contract fixed.

**Checkpoint evolution** precedes “more endpoints”: without per-stream cursors, every new endpoint re-ships shallow snapshots.

---

## B. Connector gap maps

Each connector: **(1) current**, **(2) missing**, **(3) technical limitations**, **(4) required end state**.

### B.1 Slack

#### 1) Currently ingested (as implemented in code)

| Resource type | Source | Depth | Pagination | Cursor in checkpoint | Replay |
| ------------- | ------ | ----- | ---------- | --------------------- | ------ |
| `slack.user` | `users.list` | All members up to `CORTEX_SLACK_USERS_MAX_PAGES` | Cursor pages | **Counters only** (`slack_user_pages`, `slack_user_members_seen`) — **no per-sync resume cursor persisted** | Replay-scoped idempotency keys |
| `slack.conversation` | `conversations.list` | `public_channel,private_channel`, `exclude_archived` | Cursor pages | **Counters only** | Same |
| `slack.message` | `conversations.history` | **Single request** per channel, `limit` ≤ `CORTEX_SLACK_CONVERSATIONS_HISTORY_LIMIT` | **None** (`response_metadata.next_cursor` not used) | **None** per channel | Same |
| `slack.api_error` | catch | One error blob | n/a | n/a | Same |
| `slack.scope_ping` | `_generic_scope_ping` | **Only** when `get_slack_connection_for_tenant` returns no link/token | n/a | `ping: true` | Same |

**Actual depth:** “Latest window” for **first N** channels (`CORTEX_SLACK_HISTORY_CHANNELS_PER_SYNC`), not full history. **No** threads, reactions, files, pins, DMs (unless types extended).

#### 2) Missing exhaust

| Stream | API / method (typical) | Why it matters |
| ------ | ---------------------- | -------------- |
| Message **history** (full) | `conversations.history` with `cursor` until exhausted | Reconstruct channels over time |
| Thread replies | `conversations.replies` | Escalation / coordination chains |
| Reactions | from message + `reactions.get` if needed | Consensus / priority signals |
| File metadata | `files.info` / file refs in messages | Artifacts |
| Pins / bookmarks / canvases | Slack methods per product | Organizational anchors |
| Message edits/deletes | Events API or history metadata | Truth over time |
| DMs / MPIM | `conversations.list` types `im,mpim` | **Policy-gated** (compliance) |
| Member join/leave | `team_accessLogs` / Events API | Membership drift |

**Missing temporal depth:** no `oldest`/`latest` cursor per channel; no backfill completion flag.

**Missing incremental continuation:** next sync does not reliably “continue” partial channel history.

#### 3) Technical limitations

- **Rate limits:** 429 + `Retry-After` (partially handled in `slack_web_api_post`); large workspaces → long runs.
- **Checkpoint:** monotonic merge does not yet protect **nested** cursor objects; risk of overwriting channel cursors if merge is naive.
- **Replay vs live:** live inserts may duplicate same logical message across runs (idempotency uses `run_id` in live mode).
- **Scaling:** single-task sequential fetch (users → all channels → N histories) → **timeout risk**; needs **time-budgeted chunking** or subtasks.
- **Storage:** millions of messages → large `raw_ingestion_records`; JSONB payload size per row.

#### 4) Required end state (Phase 01 complete for Slack)

- For **every** in-scope conversation type: **full** `conversations.history` pagination per channel with **checkpointed cursor** until caught up; then **incremental** mode (e.g. latest cursor or Events backlog).
- **Thread** exhaust via `conversations.replies` for each `thread_ts` discovered.
- Reactions/files/pins per matrix row **implemented or explicitly deferred** with sign-off (§F).
- `slack.scope_ping` **not** the dominant row type when connection is valid.
- Operator can **see** message volume and time span in admin aggregates.

---

### B.2 GitHub

#### 1) Currently ingested

| Resource type | Source | Depth | Pagination | Cursor in checkpoint | Replay |
| ------------- | ------ | ----- | ---------- | --------------------- | ------ |
| `github.repository` | `GET /installation/repositories` | Up to `CORTEX_GITHUB_INSTALLATION_REPOS_MAX_PAGES` | `page` / `per_page` | `github_installation_repos_pages`, `repos_fetched`, `total_count_hint` | Yes |
| `github.pull_request` | `GET /repos/{owner}/{repo}/pulls` | **First page only** per repo; first **N** repos (`CORTEX_GITHUB_PR_*`) | **No** `page` loop | `github_pull_requests_written` (**count merge only**) | Yes |
| `github.installation_repositories` / `github.sync` | errors | Error rows | n/a | partial | Yes |

#### 2) Missing exhaust

| Stream | API | Notes |
| ------ | --- | ----- |
| PR list (complete) | `/pulls` all pages | Required before per-PR detail |
| PR reviews | `/pulls/{n}/reviews` | Review latency |
| Review comments | `/pulls/comments` or review endpoints | Threaded review discussion |
| Issue comments | `/repos/.../issues/comments` | Cross-link to PRs sometimes |
| Commits | `/repos/.../commits`, compare SHAs | Delivery cadence |
| Check runs | `/repos/.../commits/{sha}/check-runs` | CI instability |
| Actions workflow runs | `/repos/.../actions/runs` | Pipeline exhaust |
| Deployments | `/repos/.../deployments` + statuses | Release health |
| Branches / tags | `/branches`, `/git/refs` or tags API | Lineage |
| PR timeline / events | GraphQL or REST timeline where stable | State transitions |
| Issues (non-PR) | `/issues` | Planning exhaust |

**Missing incremental:** no `since` / ETag / `updated` cursor per repo per stream.

#### 3) Technical limitations

- **Rate limit:** REST **5,000/h/app installation** (scale); need conditional requests where possible.
- **Checkpoint:** current merge is **numeric max** for a few keys — insufficient for **per-repo** cursor maps.
- **Payload size:** large PR/issue JSON; consider one row per response unit (already pattern).
- **Ordering:** backfill vs incremental ordering must avoid gaps (use `updated` sort + `since`).

#### 4) Required end state

- For each installation: **all repos** (within product policy), **all PRs** (paginated), **all** listed sub-resources per matrix, with **per-repo checkpoint** object.
- Dominant rows are **delivery artifacts** (PR, review, check_run, workflow_run), not repo catalog alone.
- Incremental: subsequent syncs use `since` or GraphQL `updatedAt` where adopted.

---

### B.3 Linear

#### 1) Currently ingested

| Resource type | Source | Depth | Pagination | Cursor | Replay |
| ------------- | ------ | ----- | ---------- | ------ | ------ |
| `linear.issue` | GraphQL `issues(first: n)` | **Single page**; small field selection | **No** `after` | **None** (only `linear_issues_fetched` count) | Partial |
| `linear.viewer_ping` | `viewer { id name }` | Connectivity | n/a | n/a | Partial |

#### 2) Missing exhaust

| Stream | GraphQL (conceptual) |
| ------ | -------------------- |
| Issues (complete) | `issues` with `pageInfo` + `after` |
| Incremental | filter by `updatedAt > $cursor` |
| Comments | `comment` / issue children |
| History / activity | activity feed queries |
| Labels, projects, cycles, attachments, relations | entity queries |

#### 3) Technical limitations

- GraphQL **complexity** and **rate** limits.
- **Checkpoint:** needs `updatedAt` watermark + pagination cursor.
- **Payload:** nested issue JSON; watch query cost.

#### 4) Required end state

- Full issue set + **all** attached streams in matrix, **cursor + updatedAt** incremental, **viewer_ping** optional health only.

---

### B.4 Notion

#### 1) Currently ingested

| Resource type | Source | Depth |
| ------------- | ------ | ----- |
| `notion.scope_ping` | `_generic_scope_ping` | Synthetic only |

#### 2) Missing exhaust

- `POST /v1/search` (paginated)  
- `GET/POST` databases query, pages, `blocks/{id}/children` with `start_cursor`  
- Comments / versions if API exposes  

#### 3) Technical limitations

- **3 req/s** integration default; heavy pagination.
- Large nested block trees → many rows.

#### 4) Required end state

- Real `notion.page`, `notion.block`, `notion.database` (or agreed naming) rows with **full pagination**; ping only on missing token.

---

### B.5 Calls (Gemini / meetings)

#### 1) Currently ingested

| Resource type | Source |
| ------------- | ------ |
| `calls.scope_ping` | synthetic when “connected” |

#### 2) Missing exhaust

- Transcripts, speakers, segments, recording metadata, calendar join URLs — **API TBD** per provider.

#### 3) Technical limitations

- Provider heterogeneity; OAuth scopes; PII; retention.

#### 4) Required end state

- At least one provider **fully specified** with raw resource types for transcript + metadata; or **signed deferral** in §F.

---

## C. Implementation roadmap (do not start until plan review)

Each step: **APIs**, **resource types**, **checkpoint changes**, **replay**, **payload/risk**, **deps**, **why**.

### Phase R0 — Checkpoint schema foundation (blocking)

| Step | Work | Checkpoint | Risks |
| ---- | ---- | ---------- | ----- |
| R0.1 | Define **per-connector** checkpoint JSON schema (documented in code + this file): nested maps `streams.slack.channels.{id}.history_cursor`, `streams.github.repos.{full_name}.pulls_page`, etc. | Extend `merge_monotonic_connector_state` OR use **deep merge** rules for known paths | Regressions; need tests |
| R0.2 | Migration strategy: existing flat keys remain; new keys additive | — | Backward compat |

**Why:** Without this, every connector stays “first page only.”

---

### Phase R1 — Slack deep history + threads

| ID | APIs | New/updated `resource_type` | Checkpoint | Replay | Payload / risk | Deps |
| -- | ---- | ----------------------------- | ---------- | ------ | -------------- | ---- |
| R1.1 | `conversations.history` with `cursor` loop | `slack.message` (same type; payload includes paging metadata) | Per-channel `history_cursor`, `complete` flag | Stable key: `slack:msg:{channel}:{ts}` + replay suffix | Huge volume | R0 |
| R1.2 | `conversations.replies` | `slack.message_reply` (**locked:** `phase-01-raw-persistence-doctrine.md` §2.1) | Per-thread cursor if API provides | Per reply ts | Rate limit | R1.1 |
| R1.3 | Reactions (from message + supplemental) | `slack.reaction` | optional | | | R1.1 |
| R1.4 | Files | `slack.file` | | | | R1.1 |
| R1.5 | Extend `conversations.list` types for DMs | `slack.conversation` | | | **Legal** | §F |

**Workload:** time-budget per Celery task; resume next tick.

---

### Phase R2 — GitHub delivery exhaust

| ID | APIs | `resource_type` | Checkpoint | Notes |
| -- | ---- | ----------------- | ---------- | ----- |
| R2.1 | `/pulls` all pages | `github.pull_request` | `repos.{fn}.pulls_next_page` or full list cursor | Fix “first page only” |
| R2.2 | `/pulls/{n}/reviews` | `github.pull_request_review` | per PR | |
| R2.3 | Review comments / issue comments | `github.pull_request_review_comment`, `github.issue_comment` | per PR / since | |
| R2.4 | `/commits` | `github.commit` | per repo `sha` cursor | |
| R2.5 | Check runs | `github.check_run` | per commit sha | |
| R2.6 | Actions runs | `github.workflow_run` | `page` + `created` | |
| R2.7 | Deployments | `github.deployment`, `github.deployment_status` | | |
| R2.8 | Branches/tags | `github.branch`, `github.tag` | | |

**Rate limit:** conditional requests; backoff; per-installation token rotation already via app.

---

### Phase R3 — Linear GraphQL completion

| ID | Work | Checkpoint |
| -- | ---- | ---------- |
| R3.1 | Issues: paginate `after` until done | `issues_end_cursor`, `issues_updated_at_watermark` |
| R3.2 | Incremental: `updatedAt > watermark` | |
| R3.3 | Comments, labels, projects, cycles, attachments, relations | per-entity cursors |

---

### Phase R4 — Notion crawl

| ID | APIs | `resource_type` |
| -- | ---- | --------------- |
| R4.1 | Search paginated | `notion.search_result` |
| R4.2 | Retrieve page/database + database query pagination | `notion.page`, `notion.database`, `notion.database_row` |
| R4.3 | Block children traversal (`start_cursor` continuation) | `notion.block` |

**Status:** **Implemented (Step 11 core)** in `sync_executor.py` with Notion search/database/block pagination + checkpoint resume (`streams.notion.search`, `streams.notion.database_rows.databases`, `streams.notion.blocks.parents`), time budget guard (`CORTEX_NOTION_TIME_BUDGET_SECONDS`), and integration coverage in `test_step11_notion_exhaust.py`.

---

### Phase R5 — Calls

| ID | Work |
| -- | ---- |
| R5.1 | Lock provider + OAuth + list meetings |
| R5.2 | Fetch transcript JSON + `calls.transcript`, `calls.participant` |

**Status:** **Implemented (Step 12 core)** in `sync_executor.py` with checkpointed Calls event pagination (`streams.calls.events`), meeting/participant/transcript/transcript-segment/recording raw rows, mock dataset provider path + Google Calendar events fallback, and Step 12 integration coverage in `test_step12_calls_exhaust.py`.

---

### Phase R6 — Admin explorer (exhaust verification)

| ID | Work |
| -- | ---- |
| R6.1 | Aggregates: row count, min/max `fetched_at` by `connector, resource_type` |
| R6.2 | Default hide `*.scope_ping` |
| R6.3 | Drilldown: payload search / filter by time |

**Status:** **Implemented (Step 13 core)** via admin API + frontend: `raw-stats` supports connector/resource/time filters with health-row default hide, and connector raw drilldown supports payload search + time filters + explicit health-row include.

---

### Phase R7 — Operational verification

| ID | Work |
| -- | ---- |
| R7.1 | Extend `verification.py`: fail if ping ratio > threshold **after** streams exist |
| R7.2 | Synthetic “reconstruction drill” checklist per tenant (manual script) |

**Status:** **Implemented (Step 14 core)** — verification endpoint enforces exhaust gate checks (`ping_ratio_after_streams`, multi-connector evidence, reconstruction signal coverage) and emits reconstruction-drill checklist output; runbook documented in `../01-ingestion/phase-01-reconstruction-drill-checklist.md`.

---

### Phase R8 — Live-lane logical idempotency lock

| ID | Work |
| -- | ---- |
| R8.1 | Define per-stream `source_identity_key` + `source_revision_key`; remove `run_id` from live logical identity |
| R8.2 | Implement canonical payload hashing + deterministic conflict-ignore insertion in live lane |
| R8.3 | Preserve replay/live isolation with partial unique constraints and lane-aware operator queries |
| R8.4 | Add duplicate-prevention, key-quality, and revision-churn metrics + verification gates |
| R8.5 | Roll out migration from run-scoped live keys via dual-write and compatibility phases |

**Status:** **Implemented (Step 15 core)** — raw rows now persist `source_identity_key` + `source_revision_key`, canonical source-payload hashing is used for revision fallback, live writes use conflict-ignore insertion keyed by logical identity+revision (`replay_job_id IS NULL` index), replay uniqueness remains `(replay_job_id, idempotency_key)`, and admin drilldown exposes identity/revision fields.

---

## D. Cross-cutting: replay semantics (locked)

| Option | Live lane | Replay lane |
| ------ | --------- | ----------- |
| **A (locked)** | Stable idempotency key = `connector:stream:stable_id` (no `run_id`); append once per object revision | Same key + `replay_job_id` scope |
| **B** | Legacy (pre-Step 15): key includes `run_id` → duplicate raw rows per sync | Isolated |

**Decision:** **A is mandatory** for Phase 01 closure (Step 15) per `../01-ingestion/phase-01-live-idempotency-doctrine.md`; B is non-compliant.

---

## E. Scalability & storage expectations

- **Slack messages:** 10⁶–10⁸ rows per large tenant — Postgres size + index on `(tenant_id, connector, resource_type, fetched_at)` may be needed (Phase 02 indexing may own; Phase 01 must not block on index if writes succeed).
- **Chunking:** default **max wall time per task** (e.g. 10–15 min) + checkpoint resume.
- **Retries:** exponential backoff; distinguish **4xx** (don’t retry) vs **5xx/429**.

---

## F. Open architectural decisions (require review before coding)

1. **Slack DM / compliance:** ingest DMs or exclude with legal flag?
2. **Slack thread row model:** **LOCKED** — see `../01-ingestion/phase-01-raw-persistence-doctrine.md` §2.1 (`slack.message` + `slack.message_reply`, single-message payloads).
3. **GitHub:** REST-only vs GraphQL for timeline — **one** chosen per resource for replay stability.
4. **Live idempotency:** **Closed** — Option A is mandatory via Step 15 doctrine (§D + R8).
5. **Runtime correctness hardening:** **Closed** — Step 16 mandates invariant suite + connection-scoped uniqueness + explicit connection scoping for trigger/scheduler/runtime paths.
5. **Notion:** **LOCKED default** — gated block rows; pages/DB/query rows first — see `phase-01-raw-persistence-doctrine.md` §2.4.
6. **Calls:** **Closed for Step 12 core** — Google Calendar events (OAuth token) + mock dataset transcript/recording shape for local depth validation; provider-breadth expansion remains later-phase.
7. **Deferred streams:** which matrix rows are **explicitly out of Phase 01** (if any)?

---

## G. Operational risk summary

| Risk | Mitigation |
| ---- | ---------- |
| Long-running tasks | Time budget + checkpoint resume |
| API rate limits | 429 handling, spread syncs, per-install throttles |
| Checkpoint corruption | schema validation + tests + monotonic rules |
| DB growth | monitoring; optional stable idempotency (§D) |
| Scope creep into Phase 03 | code review against `phase-01-organizational-exhaust-spec.md` §4 |

---

## H. Document control

Update **this file** when: gap map changes, roadmap step completes, or §F decisions close.
