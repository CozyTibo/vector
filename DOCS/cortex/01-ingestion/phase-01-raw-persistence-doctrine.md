# Phase 01 — Raw Persistence Doctrine (Conversational / Activity / Execution Units)

**Status:** normative — **lock before implementation** of Steps 7–15 (`MASTER_TRACKER.md`).  
**Scope:** Phase 01 **only** — physical shape of `raw_ingestion_records` (and checkpoint implications). **Not** canonicalization, ontology, graphs, retrieval UX, or embeddings.

**Related:** `phase-01-organizational-exhaust-spec.md`, **`phase-01-ingestion-continuity-doctrine.md`** (how cursors, idempotency, and live/replay advance over time), **`phase-01-live-idempotency-doctrine.md`** (mandatory live-lane identity/revision/hash semantics), `../implementation/organizational-exhaust-execution-track.md`, `raw-envelope-contract-stability.md`, `persistence-architecture.md`.

---

## 0. Problem statement

Organizational exhaust must be persisted so that:

| Requirement | Meaning |
| ----------- | ------- |
| **Replay efficiency** | Replay jobs re-fetch or re-assert **bounded** units; avoid re-materializing giant composite blobs on every run. |
| **Bounded storage** | No uncontrolled duplication of the same conversational or delivery payload across rows or runs. |
| **Reconstruction** | Time-ordered **execution movement** can be recovered from raw rows + envelopes (timestamps, ids, parent pointers **as returned by APIs**). |
| **Future canonicalization tractability** | Downstream mappers get **stable addresses** (connector, resource_type, provider ids) and **clear precedence** (append vs replace semantics documented here). |

This document answers: **what gets its own row, what stays embedded, and how threads/PRs/activity/blocks are physically stored.**

---

## 1. Recommended global raw persistence doctrine

### 1.1 Unit of persistence (default rule)

**One `raw_ingestion_record` row = one provider-addressable artifact** as returned by a **single** API call unit (or one element of a paginated list response), **unless** an explicit **composite doctrine** below says otherwise.

A **provider-addressable artifact** has at least one of:

- Stable **id** from the provider (message `ts`, comment `node_id`, review `id`, check_run `id`, block `id`, …), or  
- Stable **composite key** defined by the API contract (`channel_id + thread_ts` for a thread **parent** message only where the API does not assign a separate thread id).

### 1.2 What gets its own row vs embedded

| Persist as **own row** | Keep **embedded** in parent row payload |
| --------------------- | ---------------------------------------- |
| Object with **stable provider id** and **independent lifecycle** (reply message, review, review comment, check_run, Linear comment, Notion block **when doctrine includes blocks**) | Small **static** scalars on parent response (e.g. PR `title` at fetch time) |
| Paginated **list items** where each item is a first-class API object | **Redundant copies** of the full parent document inside every child row |
| **Distinct API fetch** (second request) for a child resource | Large **nested arrays** that are **snapshot-only** and **not** separately addressable — only if doctrine explicitly allows **snapshot rows** (see Linear caveat) |

### 1.3 Snapshot vs append stream

- **Append stream:** each new provider version → **new row** (new `fetched_at`, optional new `payload_hash`) with idempotency keyed so **identical** refetch does not insert twice.  
- **Snapshot row:** single row type overwritten in place — **not** Phase 01 default for connector APIs (append-only table). **Do not** use snapshot-in-place for raw table; use **append** with idempotency on logical version.

### 1.4 Idempotency (live lane)

For high-volume streams, **prefer** stable keys: `connector:resource_family:provider_stable_id` (and replay suffix in replay lane), **not** `run_id`, to avoid **row explosion per sync** for the same logical object. Phase 01 remains raw — this is **operational dedupe at persistence boundary**, not semantic dedupe.

This is now a hard closure requirement (Phase 01 Step 15), not optional tuning.

---

## 2. Per-connector unit model

### 2.1 Slack — thread / conversational unit

#### Decision: **Model A (disciplined) — parent message row + child reply rows**

| Row type | `resource_type` | What is stored |
| -------- | ----------------- | -------------- |
| Channel message (not a reply) | `slack.message` | One Slack message object **for that ts** only. |
| Thread parent | `slack.message` | Same — message where `thread_ts == ts`. |
| Thread reply | `slack.message_reply` | One Slack message object **for that reply ts** only (`thread_ts` set, `ts` ≠ `thread_ts`). |

**Rationale**

| Criterion | Model A | Model B (one row = full thread JSON) | Model C (hybrid) |
| --------- | -------- | -------------------------------------- | ---------------- |
| **Replay** | Re-fetch/replay **per message**; bounded | Every new reply → **re-ingest entire thread** or ambiguous merge | Must define two code paths; more bugs |
| **Duplication** | Low if payloads are **single-message** only | Risk: duplicate full thread in **every** update | Risk: parent holds thread **and** children rows duplicate text |
| **Incremental** | New reply → **one new row** + cursor advance on `conversations.history` / `replies` | Cursor semantics blur (what is “version” of thread?) | Same as A for children; parent aggregate adds rules |
| **Checkpoint** | Per-channel `latest` / `oldest` cursors for history + per-thread `replies_cursor` if needed | Single cursor per thread or channel only with pain | Heavier |
| **Temporal reconstruction** | Order by `(channel_id, ts)` and `thread_ts` grouping from payloads | Single point read | Same as A if hybrid stores children separately |
| **Canonicalization later** | Clear mapping: message id = `(channel, ts)` | One blob → splitter burden | Same |

**Doctrine rules (mandatory)**

1. **No row** may embed the **full ordered list of all replies** if those replies are also persisted as **`slack.message_reply` rows** (no duplicate full thread).  
2. Parent `slack.message` may include **Slack’s own** `reply_count` / `latest_reply` **fields** as returned by API on the parent object — that is **metadata**, not a second copy of all reply bodies.  
3. **Reactions:** default **embed** on the message object **as returned by API** on that message fetch. **Do not** create one row per reaction in Phase 01 unless a **flagged** stream `slack.reaction` is enabled later (pressure-test: optional).  
4. **Edits:** prefer **latest message payload** from history; separate `message_changed` event rows are **deferred** unless compliance requires (avoid double-counting without rules).

**Recommended single doctrine:** **A** as specified above.

---

### 2.2 GitHub — PR / delivery / activity unit

#### Decision: **One row per provider-stable delivery artifact; avoid monolithic “timeline blob” as the sole source**

| `resource_type` (illustrative) | Unit | Idempotency anchor |
| ------------------------------ | ---- | ------------------ |
| `github.pull_request` | One PR object (list or GET) | `owner/repo#number` + content `updated_at` or node id if available |
| `github.pull_request_review` | One review object | `review_id` or `(pr, submission id)` per API |
| `github.pull_request_review_comment` | One review comment | `comment_id` |
| `github.issue_comment` | One issue comment | `comment_id` |
| `github.commit` | One commit object **when fetched** | `repo:sha` |
| `github.check_run` | One check run | `check_run_id` |
| `github.workflow_run` | One workflow run (if ingested) | `workflow_run_id` |
| `github.deployment` / `github.deployment_status` | One API object | provider ids |

**What is NOT the default unit**

- **One giant row per PR containing** full timeline array as the **only** persistence — **anti-pattern** for replay (re-fetch whole timeline), checkpoint granularity, and mapper tractability.  
- **Optional exception:** a **separate** `github.timeline_event` row **per event** **only if** each event has a **stable id** from GitHub; if not, prefer **specific endpoints** (reviews, comments, commits) over undifferentiated timeline arrays.

**PR = execution spine:** always own rows. **Reviews and comments** = own rows (execution movement). **Check runs** = own rows **when** scoped to PR head / commits on the PR (pressure-test: avoid org-wide Actions firehose in MVP). **Commits:** **PR-linked commits first**; full default-branch walk **deferred**.

**Recommended doctrine:** **One row per stable REST/GraphQL object** with its own id; **no** duplicate embedding of the full PR JSON inside every review row (reviews carry only their payload + parent PR reference fields as API returns).

---

### 2.3 Linear — issue / comment / activity unit

#### Decision: **Hybrid append — discrete rows for comments + activity entries; issue body as versioned issue row**

| Stream | Persistence |
| ------ | ----------- |
| **Issue** | `linear.issue` — **append** row when issue node is fetched and **logical version** changes (idempotency: `issue:{id}:updatedAt:{updatedAt}` or equivalent stable version field from API). **Do not** silently “replace” prior row in place. |
| **Comment** | `linear.comment` — **one row per comment** with comment id. |
| **Activity / history** | **Prefer** `linear.activity` (or `linear.issue_history`) **one row per activity item** if the API exposes a list with stable ids. **If** only a nested `activity` array on issue without per-event ids, **one** `linear.issue_activity_snapshot` row per fetch **per issue** is allowed **only as interim** — document that canonicalization will treat as weak ordering; **prefer** upgrading to discrete events when GraphQL supports it. |

**Execution movement** lives in **comments + transitions**; issue snapshot alone is **under-ingesting** without activity or frequent snapshots.

**Recommended doctrine:** **Discrete rows for comments and for each activity event when ids exist**; **append-only issue rows** keyed by issue id + `updatedAt` (or hash) to cap duplication while preserving history.

---

### 2.4 Notion — page / database / block unit

#### Decision: **Page and database as rows; blocks as rows only under explicit rules**

| Unit | Row | When |
| ---- | --- | ---- |
| Database | `notion.database` | On discover / sync |
| Page | `notion.page` | On discover / sync; payload includes **properties** |
| Database row (data source) | `notion.database_row` or `notion.page` per API model | One row per row returned by `databases/{id}/query` |
| Block | `notion.block` | **Only if** (1) block has **stable `id`**, and (2) **doctrine gate** passes: e.g. **depth ≤ D**, or **type ∈ allowlist** (`child_database`, `to_do`, `callout`, …), or **explicit “deep sync”** flag for page |

**Hierarchy:** store **`parent_id` / `parent.type`** from API in payload — **no** inferred graph.

**Default Phase 01:** **properties-first** — most execution signal in DB rows and page properties; **full block tree** is **not** required for Phase 01 “lean” closure if matrix defers it.

**Recommended doctrine:** **Row per page/database/query row**; **block rows** only for gated depth/types or flagged pages — never “every block for every page” as mandatory default.

---

### 2.5 Calls — meeting / transcript unit

| Unit | Row | Notes |
| ---- | --- | ----- |
| Meeting / call | `calls.meeting` (or provider name) | Metadata: id, time, title, organizer |
| Transcript segment | `calls.transcript_segment` **or** single `calls.transcript` with **array in payload** | If provider gives **segments with ids** → **prefer one row per segment** for replay; if only one blob → **one row per meeting** with array (bounded size) |
| Participant | Embed on meeting row **or** `calls.participant` rows if API lists them with ids | Prefer **rows** if stable participant ids exist |

**Defer:** raw audio/video files.

---

## 3. Anti-patterns to avoid

1. **Full thread / full PR timeline / full Notion page tree** duplicated inside **every** child row.  
2. **One row per sync** that dumps **unbounded JSON** (entire workspace) without pagination metadata.  
3. **Live idempotency = `run_id`** for high-volume stable objects → **unbounded append explosion**.  
4. **Timeline-only** GitHub ingest without per-event ids → **replay ambiguity**.  
5. **Embedding reactions as thousands of child rows** by default → noise (Slack).  
6. **In-place overwrite** of raw rows (violates append-only evidence model).  
7. **Checkpoint** that stores **entire message arrays** instead of cursors.

---

## 4. Replay / storage / query tradeoffs (summary)

| Pattern | Storage | Replay | Incremental | Query later |
| ------- | ------- | ------ | ----------- | ----------- |
| **One row per message (Slack A)** | Linear in messages | Replay subset by id | Easy | Filter by `resource_type`, `external_id` prefix |
| **One row per thread blob** | Lower row count | Must re-pull whole blob | Hard | Single read, bad diff |
| **One row per GitHub artifact** | Moderate | Per-artifact keys | Easy | Clean joins in Phase 02+ |
| **Notion blocks all** | Huge | Heavy | Rate limit hell | Noisy |

---

## 5. Scaling implications

- **Row count** grows with **messages, comments, check_runs** — expected; **mitigate** with stable idempotency and **chunked sync**.  
- **Payload size** — prefer **one API object per row**; avoid **N×** duplicate parent.  
- **Checkpoint JSON** — many channels/repos → **large state**; if needed, **cursor side-table** (still Phase 01 operational data) per tenant/connector/scope.  
- **Celery** — one task must not hold **whole workspace**; **batch by channel/repo/issue page**.

---

## 6. Canonicalization compatibility (non-design)

Patterns that help **later** phases **without designing them**:

- **Stable external ids** in envelope + `resource_type` granularity aligned to **provider objects**.  
- **Append-only** issue/PR **versions** with clear `updatedAt` / timestamps in payload.  
- **Avoid** ambiguous composite blobs as the **only** source of truth.  
- **Thread / PR parent ids** present on children **as API provides** — mappers use them without Vector inferring edges.

---

## 7. Recommended final Phase 01 persistence shape (concise)

1. **Default:** one row = **one provider-stable object** from API.  
2. **Slack threads:** **`slack.message` + `slack.message_reply`**, single-message payloads only; no full-thread duplication.  
3. **GitHub:** **Separate rows** for PR, review, review comment, issue comment, commit (when fetched), check_run (scoped); **no** timeline-only monolith.  
4. **Linear:** **Append issue rows** versioned by `updatedAt` (or hash); **comment rows**; **activity rows** when ids exist.  
5. **Notion:** **Database + page + query rows**; **blocks** gated.  
6. **Calls:** **Meeting + transcript** (segment rows if ids exist).  
7. **Cross-cutting:** **stable idempotency** for live lane on hot paths; **embed** small API-included fields; **defer** exhaustive derived enumerations (reactions-as-rows, every block).

---

## 8. Document control

| Change | Action |
| ------ | ------ |
| New `resource_type` | Update matrix, registry, **this doctrine** if unit boundary changes |
| Slack thread model | **Locked §2.1** — changing requires ADR |

**Next step:** Record open flags (e.g. Notion depth D, GitHub workflow scope) in `organizational-exhaust-execution-track.md` §F and env defaults.
