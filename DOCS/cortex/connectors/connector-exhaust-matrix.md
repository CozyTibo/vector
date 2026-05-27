# Connector Exhaust Matrix (Completeness Tracker)

**Canonical purpose:** this matrix is the **organizational exhaust completeness tracker** — not the Phase 01 substrate step table, not “connector health,” not maturity tooling.

**Normative Phase 01 exhaust definition + exit criteria:** `../01-ingestion/phase-01-organizational-exhaust-spec.md`.  
**Mandatory final hardening gate:** `../01-ingestion/phase-01-live-idempotency-doctrine.md` (Step 15 live-lane logical idempotency).  
**Gap truth + implementation roadmap:** `../implementation/organizational-exhaust-execution-track.md`.

**Machine-readable mirror:** `backend/src/vector/domains/cortex/ingestion/exhaust_coverage_registry.py` + admin `GET /admin/tenants/{tenant_id}/cortex/ingestion/exhaust-coverage`.

Legend: **Coverage** `none` | `partial` | `full` · **Historical** `none` | `partial` | `full` · **Replay** `no` | `partial` | `yes` · **Canon** `none` | `partial` | `full` · **Status** `missing` | `in_progress` | `active`

## Slack

| Resource type   | Coverage | Historical | Replay | Canon | Status      | Notes |
| --------------- | -------- | ---------- | ------ | ----- | ----------- | ----- |
| `slack.user`    | partial  | partial    | partial| none  | in_progress | `users.list` cursor pages (env `CORTEX_SLACK_USERS_MAX_PAGES`) |
| `slack.channel_member` | partial | partial | partial | none | in_progress | `conversations.members` for ring-selected channels (capped) |
| `slack.conversation` | partial | partial | partial | none | in_progress | `conversations.list` public+private (env `CORTEX_SLACK_CONVERSATIONS_MAX_PAGES`) |
| `slack.message_changed` | partial | partial | partial | none | in_progress | History rows with `subtype=message_changed` |
| `slack.message` | full | partial    | partial| none  | in_progress | `conversations.history` paginated with per-channel checkpoint cursors (`CORTEX_SLACK_HISTORY_MAX_PAGES_PER_CHANNEL`) and round-robin channel resume |
| `slack.message_reply` | partial | partial | partial | none | in_progress | `conversations.replies` ingested for discovered thread roots; per-thread checkpoint cursors |
| `slack.reaction`       | partial     | partial       | partial     | none  | in_progress     | Message-embedded reactions captured from history pages |
| edits           | none     | none       | no     | none  | missing     | |
| `slack.pin` | partial | partial | partial | none | in_progress | `pins.list` per ring channel (requires `pins:read`) |
| `slack.file`      | partial     | partial       | partial     | none  | in_progress     | Message-embedded file metadata captured from history pages |
| scope_ping (health) | partial | n/a       | partial| none  | in_progress | Only when Slack detail / bot token missing |

## GitHub

| Resource type        | Coverage | Historical | Replay | Canon | Status      | Notes |
| -------------------- | -------- | ---------- | ------ | ----- | ----------- | ----- |
| `github.user` | partial | partial | partial | none | in_progress | `GET /orgs/{org}/members` for Organization installations |
| `github.team` | partial | partial | partial | none | in_progress | `GET /orgs/{org}/teams` |
| `github.team_membership` | partial | partial | partial | none | in_progress | `GET /orgs/{org}/teams/{slug}/members` |
| `github.installation_repositories` (API list) | partial  | partial    | partial| none  | in_progress | Paginated `page`+`per_page` up to `CORTEX_GITHUB_INSTALLATION_REPOS_MAX_PAGES` per sync |
| `github.repository` (per-repo raw row) | partial  | partial    | partial| none  | in_progress | One row per repo returned across paginated installation scan |
| `github.pull_request` | full | partial    | partial | none | in_progress | Paginated `/pulls` with per-repo checkpoint page continuity; bounded by `CORTEX_GITHUB_PRS_MAX_PAGES_PER_REPO` |
| `github.pull_request_review` | partial | partial | partial | none | in_progress | Paginated `/pulls/{n}/reviews` for ingested PRs |
| `github.pull_request_review_comment` | partial | partial | partial | none | in_progress | Paginated `/pulls/{n}/comments` for ingested PRs |
| `github.issue_comment` | partial | partial | partial | none | in_progress | Paginated `/issues/{n}/comments` for ingested PRs |
| `github.commit` | partial | partial | partial | none | in_progress | Paginated `/commits` with per-repo cursor continuity |
| `github.check_run` | partial | partial | partial | none | in_progress | Paginated check-runs for PR head SHAs |
| `github.workflow_run` | partial | partial | partial | none | in_progress | Paginated `/actions/runs` with per-repo cursor continuity |
| `github.deployment` | partial | partial | partial | none | in_progress | Paginated `/deployments` with per-repo cursor continuity |
| `github.deployment_status` | partial | partial | partial | none | in_progress | Paginated deployment statuses per deployment |
| `github.branch` | partial | partial | partial | none | in_progress | Paginated `/branches` with per-repo cursor continuity |
| `github.tag` | partial | partial | partial | none | in_progress | Paginated `/tags` with per-repo cursor continuity |

## Linear

| Resource type   | Coverage | Historical | Replay | Canon | Status      | Notes |
| --------------- | -------- | ---------- | ------ | ----- | ----------- | ----- |
| `linear.user` | partial | partial | partial | none | in_progress | GraphQL `users` connection (people plane) |
| `linear.team` | partial | partial | partial | none | in_progress | GraphQL `teams` + memberships |
| `linear.team_membership` | partial | partial | partial | none | in_progress | Team member edges from teams query |
| `linear.issue`  | full     | partial    | partial| none  | in_progress | GraphQL issues paginated with `pageInfo.endCursor` + incremental `updatedAt` watermark checkpoints; assignee/creator on query |
| `linear.comment` | partial | partial | partial | none | in_progress | GraphQL comments connection, checkpoint cursor continuity |
| `linear.project` | partial | partial | partial | none | in_progress | GraphQL projects connection |
| `linear.cycle` | partial | partial | partial | none | in_progress | GraphQL cycles connection |
| `linear.issue_relation` | partial | partial | partial | none | in_progress | GraphQL issueRelations connection |
| `linear.issue_label` | partial | partial | partial | none | in_progress | GraphQL issueLabels connection |
| `linear.initiative` | partial | partial | partial | none | in_progress | GraphQL initiatives connection |
| `linear.issue_attachment` | partial | partial | partial | none | in_progress | Extracted from issue payload when attachments are present |
| `linear.activity_history` | partial | partial | partial | none | in_progress | Extracted from issue payload when activity/history is present |
| `linear.viewer_ping` | partial | n/a | partial | none | active | Connectivity snapshot retained; non-exhaust by itself |

## Notion

| Resource type   | Coverage | Historical | Replay | Canon | Status      | Notes |
| --------------- | -------- | ---------- | ------ | ----- | ----------- | ----- |
| `notion.user` | partial | partial | partial | none | in_progress | `GET /v1/users` before search/structure |
| `notion.search_result` | partial | partial | partial | none | in_progress | Paginated `/search` traversal with checkpointed `next_cursor` and incremental watermark |
| `notion.page` | partial | partial | partial | none | in_progress | Pages discovered via search and database row scans |
| `notion.database` | partial | partial | partial | none | in_progress | Database metadata from `/databases/{id}` for discovered databases |
| `notion.database_row` | partial | partial | partial | none | in_progress | Paginated `/databases/{id}/query` with per-database cursor continuity |
| `notion.block` | partial | partial | partial | none | in_progress | Paginated `/blocks/{id}/children` traversal with per-parent checkpoint continuity |
| `notion.scope_ping` | partial | n/a | partial | none | in_progress | Connectivity row emitted alongside deep streams; non-exhaust by itself |

## Calls (Gemini)

| Resource type   | Coverage | Historical | Replay | Canon | Status      | Notes |
| --------------- | -------- | ---------- | ------ | ----- | ----------- | ----- |
| `calls.meeting` | partial | partial | partial | none | in_progress | Paginated meeting/event ingestion (mock dataset + Google Calendar events API fallback) |
| `calls.participant` | partial | partial | partial | none | in_progress | Per-meeting attendees persisted when available |
| `calls.transcript` | partial | partial | partial | none | in_progress | Transcript payload persisted when provider returns transcript object |
| `calls.transcript_segment` | partial | partial | partial | none | in_progress | Segment rows extracted from transcript segment arrays |
| `calls.recording` | partial | partial | partial | none | in_progress | Recording metadata rows when provider includes recording details |
| `calls.scope_ping` | partial | n/a | partial | none | in_progress | Connectivity row retained; non-exhaust by itself |

---

**Update protocol:** when executor code gains a stream, update **this file** and **`exhaust_coverage_registry.py`** in the same PR so admin UI and docs cannot drift silently.

**Closure note:** Stream coverage in this matrix is necessary but insufficient for Phase 01 closure; live-lane logical idempotency Step 15 is also required.
