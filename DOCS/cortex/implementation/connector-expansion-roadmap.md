# Connector Expansion Roadmap (Operational Ingestion)

**Purpose:** execution sequencing for **organizational exhaust depth** — complements phase steps in `MASTER_TRACKER.md` (which track substrate, contracts, and admin closure).

**Truth source for “what works today”:** `connector-exhaust-matrix.md` + `exhaust_coverage_registry.py`.

**Execution checklist (mechanics + caps):** `organizational-exhaust-execution-track.md`.

## Recently shipped (keep matrix/registry in sync)

- **GitHub:** installation repository list is **paginated** per sync (`CORTEX_GITHUB_INSTALLATION_REPOS_MAX_PAGES`); one `github.repository` raw row per repo returned.
- **Slack:** `slack.user`, `slack.conversation`, bounded `slack.message` via Web API (`CORTEX_SLACK_*` settings).
- **Linear:** `linear.issue` first page per sync (`CORTEX_LINEAR_ISSUES_FIRST`) plus viewer ping.

## Global principles

1. **Depth before polish:** prove pagination + checkpoint + raw envelope for each stream before widening parallel fan-out.
2. **Incremental before backfill:** get forward incremental safe, then bounded historical windows with operator-visible caps.
3. **Replay contracts:** any stream participating in replay must meet idempotency + envelope rules before Level 4 claims.
4. **Canon readiness:** Phase 03 mappers declare minimum raw fields — drive “Canon” column in the matrix.

## GitHub (priority: high — already partial repos list)

| Target | Current | Next milestone |
| ------ | ------- | -------------- |
| Repos (all pages) | First page | Cursor pagination + checkpoint `Link` / page index |
| Default branch commits | Missing | Per-repo commit list with since/checkpoint |
| PRs + files + comments | Missing | REST or GraphQL strategy per rate limits |
| Reviews, checks, workflows | Missing | After PR spine stable |

**Blockers:** rate limits, large installation cardinality, token refresh, mock vs prod parity tests.

## Linear

| Target | Current | Next milestone |
| ------ | ------- | -------------- |
| Viewer | Ping only | Keep as health; add **issues** incremental with GraphQL cursors |
| Comments / history | Missing | Issue timeline queries |
| Projects / cycles / relations | Missing | After issue spine |

**Blockers:** GraphQL complexity budget, webhooks vs poll (future), mock completeness.

## Slack

| Target | Current | Next milestone |
| ------ | ------- | -------------- |
| Conversations history | Missing | channels list + `conversations.history` with cursor |
| Threads | Missing | `replies` fetch policy |
| Reactions / edits | Missing | After message spine |

**Blockers:** compliance (DMs), retention, rate limits, enterprise grid variance.

## Notion

| Target | Current | Next milestone |
| ------ | ------- | -------------- |
| Search / list | Missing | Workspace scan strategy |
| Databases + rows | Missing | Data source pagination |

**Blockers:** Notion API pagination + size limits, large workspaces.

## Calls

| Target | Current | Next milestone |
| ------ | ------- | -------------- |
| Meaningful resource fetch | Meetings + participants + transcript(+segments when present) + recording metadata (Step 12 core) | Broaden provider coverage + stricter transcript source contracts |

---

Review cadence: **weekly** during active ingestion expansion; update matrix + registry in the same change as code.
