# Canon lifecycle substrate audit v1

**Date:** 2026-05-29  
**Scope:** All canonized entity types across Slack, GitHub, Linear, Notion, and Calls.  
**Goal:** Identify which types expose enough **deterministic** temporal signals for lifecycle reasoning (`planned` / `active` / `completed` / `archived` / `stale`).

## Substrate contract (v1)

Shared helpers live in `canon/lifecycle_substrate.py`:

| Attr | Purpose |
|------|---------|
| `provider_created_at` | Provider-native creation timestamp (ISO or Slack epoch string) |
| `provider_updated_at` | Provider-native last-modified timestamp |
| `archived` / `in_trash` | Explicit retirement flags |
| `status_name` / `status_id` / `workflow_state` | Workflow position |
| `lifecycle_phase` | Derived: `planned`, `active`, `completed`, `archived`, `cancelled`, `unknown` |

**Stale** is not a provider field — it is an **observation** signal (no `provider_updated_at` / activity within N days). Declared domains already approximate this via `events_7d` + `mass_total` → `dormant` bucket in `execution_surfaces/lifecycle.py`.

Mapper version bumped to **2** (`CANON_MAPPER_VERSION`) to trigger re-materialization.

---

## Entity-type readiness matrix

Legend: **Full** = timestamps + status/archived + `lifecycle_phase`. **Partial** = some signals. **None** = no lifecycle substrate. **N/A** = not materialized.

### Slack

| Entity type | Resource types | Lifecycle readiness | Signals present | Gaps |
|-------------|----------------|---------------------|-----------------|------|
| `actor` | slack.user | None | display name | No temporal |
| `conversation` | slack.conversation, slack.thread | None | channel/thread ids | No `provider_*`, no status |
| `message` | slack.message, slack.message_changed, slack.message_reply | **Partial** | `provider_created_at`/`updated_at` ← `ts` | No edit/delete/archived; stale via observation only |

### GitHub

| Entity type | Resource types | Lifecycle readiness | Signals present | Gaps |
|-------------|----------------|---------------------|-----------------|------|
| `actor` | github.user | None | login | No temporal |
| `project` | github.repository | None | full_name | No repo archived flag on canon |
| `pull_request` | github.pull_request | **Full** | `state`, `created_at`, `updated_at`, `lifecycle_phase` | `merged_at`/`closed_at` not copied |
| `work_item` | github.issue | **Full** | same as PR | `closed_at` not copied |
| `message` | issue_comment, review, review_comment, commit_comment | Partial | author ref | No message timestamp on attrs (raw only) |
| `conversation` | github.review_thread | None | — | — |
| `commit` | github.commit, commits | Partial | sha | `author_date`/`committer_date` not on attrs |
| `deployment` | workflow_run, deployment | None | — | Defer status fields |
| `release` | github.release | None | — | `published_at` not copied |

### Linear

| Entity type | Resource types | Lifecycle readiness | Signals present | Gaps |
|-------------|----------------|---------------------|-----------------|------|
| `work_item` | linear.issue | **Full** | `createdAt`, `updatedAt`, state.name, `lifecycle_phase` | `completedAt`/`canceledAt` not copied |
| `project` | linear.project | Partial | raw `state` string only | No `provider_*`, no `lifecycle_phase` |
| `cycle` | linear.cycle | **Partial** | `starts_at`, `ends_at`, `completed_at` | Not wired through lifecycle_substrate |
| `initiative` | linear.initiative | None | name | No status/temporal on canon |
| `team`, `label`, `issue_relation` | various | None / N/A | identifiers | Not execution entities |
| `message` | linear.comment | None | author | No timestamp on attrs |
| `conversation` | linear.comment_thread | None | — | — |
| `actor` | linear.user | None | — | — |

### Notion

| Entity type | Resource types | Lifecycle readiness | Signals present | Gaps |
|-------------|----------------|---------------------|-----------------|------|
| `project` | notion.database | **Partial** | `created_time`, `last_edited_time`, `archived` | No row-level status; container only |
| `document` | notion.page, notion.block, notion.database_row (unpinned) | **Partial** | temporal + archived; rows without execution props | Unpinned rows lack status |
| `work_item` | notion.database_row (pinned DB) | **Full** | temporal, status/select/date/checkbox props, `lifecycle_phase` | Custom status vocab per tenant |
| `actor` | notion.user | None | name | No temporal |

**Notion upgrade (this PR):** pinned `database_row` → `work_item`; execution property copy; relation/people graph edges; block `rich_text` in text scan.

### Calls

| Entity type | Resource types | Lifecycle readiness | Signals present | Gaps |
|-------------|----------------|---------------------|-----------------|------|
| All | calls.* | **N/A (defer)** | Raw payloads may include start/end | Registry disposition `defer` — no canon entities |

---

## Types with enough signal for lifecycle reasoning

These can support deterministic **planned / active / completed / archived** today (stale via observation):

| Connector | Entity types | Mechanism |
|-----------|--------------|-----------|
| Linear | `work_item` | Issue state + timestamps |
| GitHub | `pull_request`, `work_item` (issue) | `state` + timestamps |
| Notion | `work_item` (pinned rows), `project`/`document` (archived/temporal only) | Status property + Notion archived flags |
| Slack | `message` | Temporal only → **active vs stale**, not workflow phase |
| Declared domains | seed `project` + stats | Provider phase on seed + `events_7d` → dormant |

---

## Remaining gaps by connector

### Slack
- **Gap:** Conversations and threads have no `provider_*`; messages lack deleted/edited lifecycle.
- **Minimum addition:** Copy `latest`/`updated` channel metadata when present; optional `message_deleted` flag from `message_changed` tombstones.

### GitHub
- **Gap:** PR/issue lack `closed_at`/`merged_at`; messages/commits lack temporal attrs; repository has no archived flag.
- **Minimum addition:** `apply_temporal_attrs(..., provider_updated_at=closed_at)` when closed; copy `merged_at` to attrs; message `created_at` on comment entities.

### Linear
- **Gap:** `project`, `cycle`, `initiative` not using lifecycle_substrate; comments lack timestamps.
- **Minimum addition:** `finalize_execution_attrs` on `linear.project` from `state`; map `cycle.completed_at` → phase completed; comment `createdAt`.

### Notion
- **Gap:** Unpinned pages/rows remain `document` without status; free pages not execution entities.
- **Minimum addition:** Already addressed for pinned work DBs; optional page-type heuristics remain out of scope (no new entity types).

### Calls
- **Gap:** Entire connector deferred — no canon materialization.
- **Minimum addition:** Map `calls.meeting` → `conversation` or new `meeting` entity with `started_at`, `ended_at`, `status`; map `calls.transcript` → `document` with temporal only.

---

## Minimum canonical additions (substrate-wide)

1. **Universal temporal pair** — Every mapped entity type should set `provider_created_at` and `provider_updated_at` when the raw payload exposes them (Slack `ts`, GitHub/Linear ISO fields, Notion `*_time`).

2. **Universal retirement flags** — Copy provider `archived`, `closed`, `merged`, `cancelled`, `in_trash` into normalized `archived` or dedicated attrs where unambiguous.

3. **Status normalization** — `status_name` + optional `workflow_state`; derive `lifecycle_phase` via `finalize_execution_attrs()` at end of every execution mapper.

4. **Completion timestamps** — Add optional `provider_completed_at` (Linear `completedAt`, GitHub `closed_at`, Notion date property with “Done” semantics) — **deferred to v2**; v1 uses status names only.

5. **Observation stale** — Keep `stale`/`dormant` in declared-domain stats layer (`events_7d`, `provider_updated_at` when indexing activity) — not on entity attrs.

6. **Registry** — Per-connector status vocab extensions in `lifecycle_substrate.py` (tenant-specific Notion status names) without new entity types.

---

## Graph / execution surfaces

| Capability | Status |
|------------|--------|
| Notion relation → `references` | Implemented |
| Notion people → `assigned_to` / `involves` | Implemented |
| Block body text scan | Implemented |
| Declared domain lifecycle buckets | Uses `lifecycle_phase` + observation |
| Activity indexing on `provider_updated_at` | Partial (`temporal_ordering.py` candidates extended) |

---

## Recommended next PRs

1. GitHub: `closed_at`/`merged_at` + comment timestamps  
2. Linear: project/cycle lifecycle + comment temporal  
3. Calls: enable `calls.meeting` materialization with temporal attrs  
4. Declared domains: prefer `provider_updated_at` over `materialized_at` for member activity stats
