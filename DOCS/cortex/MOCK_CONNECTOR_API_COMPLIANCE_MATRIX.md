# Cortex connector API ↔ mock compliance matrix

Formal audit of **what Vector calls in production** vs **official vendor documentation** vs **`backend/mock_connectors` parity`.

### Latest mock tightening

Recent changes align mocks more tightly with vendor envelopes Vector parses (Notion search/page-or-data-source list shape, legacy database query list JSON, rich-text annotations, Slack thread parent fields, GitHub installation token metadata, Calendar events list metadata, Linear `projectUpdates` handler + fixtures). **True byte-for-byte parity for every optional vendor field is still not guaranteed** without automated golden fixtures sourced from live APIs.

---

## Methodology

| Column | Meaning |
|--------|---------|
| **Production call** | HTTP method + path (relative to configured base URL) or Web API method name, as implemented in `backend/src/vector/domains/cortex/connectors/**` and `sync_executor.py`. |
| **Request (Vector)** | Body/query/header arguments Vector sends today (not the union of everything the vendor allows). |
| **Doc authority** | Canonical vendor reference for **contract** (methods, parameters, response object schemas). |
| **Compliance verdict** | **Full**: Same verb/path/meaningful params + responses usable without shim quirks beyond trimming unused fields. **Partial**: Subset/simplified payloads or behavioral drift documented inline. **Mock-internal**: Not a vendor API (fixture ferry only). |

**Important limits**

- “Required fields” in vendor docs usually distinguish **required request parameters** vs **every property on response objects**. This matrix lists **what Vector depends on for ingestion** in the **Depend-on / ingest assumptions** column, not a full OpenAPI dump.
- GitHub REST responses vary by preview headers and API version; Vector pins **`Accept: application/vnd.github+json`** and **`X-GitHub-Api-Version: 2022-11-28`** on REST polls (`github/http_client.py`).
- Mock mode swaps **data-plane hostnames only where documented** in `settings.py` (`github_rest_api_base_url`, `notion_api_base_url`, `linear_graphql_url`, Slack base URL, Google Calendar base URL); App JWT installation lookups remain **real** (`github_rest_api_app_install_base_url`).

---

## Legend shortcut

| Verdict | Description |
|---------|-------------|
| ✅ Full | Same resource identity & verbs Vector expects; mock shaped for ingestion code paths. |
| ⚠️ Partial | Intentionally reduced schema or Slack-/REST-compat quirks called out below. |
| — | OAuth/admin bootstrap — identical URLs where configured to prod endpoints (mock bypass unused). |

---

## GitHub — OAuth & App lifecycle

| Production call | Request (Vector) | Depend-on / ingest assumptions | Primary docs | Mock parity |
|----------------|-----------------|----------------------------------|--------------|-------------|
| `POST https://github.com/login/oauth/access_token` | Form body: `client_id`, `client_secret`, `code`; JSON Accept | JSON `{access_token}` (+ optional refresh/expiry) | [Authorize OAuth apps](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps) | — *(never mocked)* |
| `GET https://api.github.com/app/installations/{installation_id}` | JWT bearer App auth | Installation metadata dict | [REST Apps — Get installation](https://docs.github.com/en/rest/apps/apps#get-an-installation-for-the-authenticated-app) | — *(always prod)* |
| `POST /app/installations/{installation_id}/access_tokens` | Empty POST body | JSON `{token, expires_at, permissions, repository_selection}` | [REST Apps — Create installation access token](https://docs.github.com/en/rest/apps/apps#create-an-installation-access-token-for-an-app) | ✅ Mock adds representative `permissions` + `repository_selection` fields |
| `GET /installation/repositories` | Query `page`, `per_page` | JSON object `{repositories: [...], total_count?}` | [REST Apps — List repositories accessible to installation](https://docs.github.com/en/rest/apps/installations#list-repositories-accessible-to-the-app-installation) | ✅ Mock matches envelope ingestion parses |

---

## GitHub — REST polling (`sync_executor` + `connectors/github/http_client.py`)

| Production path | Method | Request (Vector) | Depend-on / ingest assumptions | Primary docs | Mock parity |
|----------------|--------|-----------------|----------------------------------|--------------|-------------|
| `/repos/{owner}/{repo}/pulls` | GET | `state=all`, `sort=updated`, `direction=desc`, `page`, `per_page` | JSON array of pull objects | [REST pulls — List](https://docs.github.com/en/rest/pulls/pulls#list-pull-requests) | ✅ |
| `/repos/{owner}/{repo}/pulls/{n}/reviews` | GET | `page`, `per_page` | JSON array review objects | [REST pulls — List reviews](https://docs.github.com/en/rest/pulls/reviews#list-reviews-for-a-pull-request) | ✅ |
| `/repos/{owner}/{repo}/pulls/{n}/comments` | GET | `page`, `per_page` | JSON array PR review comment objects (`id`, `in_reply_to_id`, …) | [REST pulls — List review comments](https://docs.github.com/en/rest/pulls/comments#list-review-comments-on-a-pull-request) | ✅ *(minimal synthetic threads)* |
| `/repos/{owner}/{repo}/issues/{issue_number}/comments` | GET | `page`, `per_page` | JSON array issue comment objects | [REST issues — List comments](https://docs.github.com/en/rest/issues/comments#list-issue-comments) | ✅ |
| `/repos/{owner}/{repo}/commits` | GET | `page`, `per_page` | JSON array commit objects | [REST repos — List commits](https://docs.github.com/en/rest/commits/commits#list-commits) | ✅ |
| `/repos/{owner}/{repo}/commits/{ref}/check-runs` | GET | `page`, `per_page` | JSON object `{total_count, check_runs:[…]}` (nested array — **not** top-level array) | [REST checks — List check runs for a Git reference](https://docs.github.com/en/rest/checks/runs#list-check-runs-for-a-git-reference) | ✅ Rows include nested `check_suite` + REST URLs/metadata aligned with GitHub check-run objects |
| `/repos/{owner}/{repo}/actions/runs` | GET | `page`, `per_page` | JSON object `{workflow_runs, total_count}` | [REST actions — List workflow runs](https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-repository) | ✅ Synthetic runs mirror workflow-run envelope (ids, head SHA, suite linkage, URLs) |
| `/repos/{owner}/{repo}/deployments` | GET | `page`, `per_page` | JSON array of deployments | [REST deployments — List](https://docs.github.com/en/rest/deployments/deployments#list-deployments) | ✅ |
| `/repos/{owner}/{repo}/deployments/{deployment_id}/statuses` | GET | `page`, `per_page` | JSON array statuses | [REST deployments — List deployment statuses](https://docs.github.com/en/rest/deployments/statuses#list-deployment-statuses) | ✅ |
| `/repos/{owner}/{repo}/branches` | GET | `page`, `per_page` | JSON array branch summaries (`name`, `commit.sha`) | [REST branches — List branches](https://docs.github.com/en/rest/branches/branches#list-branches) | ✅ |
| `/repos/{owner}/{repo}/tags` | GET | `page`, `per_page` | JSON array tag refs | [REST repos — List repository tags](https://docs.github.com/en/rest/repos/repos#list-repository-tags) | ✅ |
| `/repos/{owner}/{repo}/comments` | GET | `page`, `per_page` | JSON array commit (=repo) comments | [REST repos — List commit comments](https://docs.github.com/en/rest/commits/comments#list-commit-comments-for-a-repository) | ✅ One deterministic comment per fixture commit (`id`, `node_id`, `commit_id`, URLs, user, timestamps) |
| `/repos/{owner}/{repo}/releases` | GET | `page`, `per_page` | JSON array releases (`id`, asset metadata subset acceptable to ingestion) | [REST releases — List](https://docs.github.com/en/rest/releases/releases#list-releases) | ✅ *(fixture-backed releases)* |
| `/repos/{owner}/{repo}/issues` | GET | `state=all`, `page`, `per_page` | JSON array issues (must tolerate PR-shaped rows filtered via `pull_request`) | [REST issues — List repository issues](https://docs.github.com/en/rest/issues/issues#list-repository-issues) | ✅ |
| `/installation/repositories` | GET | `page`, `per_page` | Repository stubs compatible with downstream pulls scope | See Apps installs docs linked above | ✅ |

---

## Slack Web API (`connectors/slack/ingestion_api.py`)

Production encoding: **`POST {SLACK_API_BASE}/{method}`** with **`Authorization: Bearer`** + **`Content-Type: application/json`** (matches Slack’s modern recommendations).

| Web API method | Request JSON keys Vector sends | Depend-on / ingest assumptions | Primary docs | Mock parity |
|----------------|-------------------------------|-------------------------------|--------------|-------------|
| `users.list` | `limit`, cursor pagination via `cursor` | `{ok:true, members:[…], response_metadata.next_cursor}` | [users.list](https://api.slack.com/methods/users.list) | ✅ Members include `team_id`, `profile.email`, `profile.display_name`, `is_bot`, `deleted`, etc. (still not every optional Slack field) |
| `conversations.list` | `types`, `exclude_archived`, `limit`, cursor | `{ok:true, channels:[…]}` | [conversations.list](https://api.slack.com/methods/conversations.list) | ✅ Channels include `is_channel`, `is_private`, `is_general`, … |
| `conversations.history` | `channel` (**required**), `limit`, optional `cursor`, `oldest`, `latest`, `inclusive` | `{ok:true, messages:[…]}` — threaded parents expose `reply_count`, `reply_users_count`, `thread_ts`, `latest_reply` | [conversations.history](https://api.slack.com/methods/conversations.history) | ✅ Mock derives parent-thread counters from fixture replies before pagination |
| `conversations.replies` | `channel`, `ts` (thread root), `limit`, optional pagination/time bounds | `{ok:true, messages:[…]}` ordered oldest→newest typical | [conversations.replies](https://api.slack.com/methods/conversations.replies) | ✅ |

---

## Notion (`sync_executor._notion_sync` when mock=false)

Base URL resolves to **`https://api.notion.com/v1`** (prod) or **`{mock}/notion/v1`**.

| Path | Method | Request JSON / URL shape | Depend-on / ingest assumptions | Primary docs | Mock parity |
|------|--------|--------------------------|-------------------------------|--------------|-------------|
| `/oauth/token` | POST | JSON `{grant_type, code, redirect_uri}` + basic auth client credentials (`connectors/notion/http_client.py`) | `access_token` (+ workspace metadata optional) | [Authorization exchange](https://developers.notion.com/reference/create-a-token) | — *(prod endpoint)* |
| `/search` | POST | `{page_size, sort?, start_cursor?}` | Paginated list with `object`, `type`, `page_or_data_source`, `results`, `has_more`, `next_cursor` | [Search](https://developers.notion.com/reference/post-search) | ✅ List envelope matches current API; fixture-derived ordering by `last_edited_time` |
| `/databases/{id}` | GET | — | Database schema-style dict | [Retrieve a database](https://developers.notion.com/reference/retrieve-a-database) | ✅ |
| `/databases/{id}/query` | POST | `{page_size, start_cursor?}` | Legacy query list `{object, results, has_more, next_cursor}` | [Query a database](https://developers.notion.com/reference/post-database-query) | ⚠️ Filters/sorts not implemented (paging only); row pages shaped as Notion page objects |
| `/blocks/{id}/children` | GET | Query-string **`page_size`**, **`start_cursor`** appended manually (`sync_executor`) | Block-child list `{object, type, block, results, has_more, next_cursor}` | [Retrieve block children](https://developers.notion.com/reference/get-block-children) | ✅ Rich-text items include annotation defaults; not every optional block property |

Headers enforced (`Authorization`, **`Notion-Version`** default `2022-06-28`): [`settings.py`](../../backend/src/vector/settings.py) (`NOTION_VERSION`).

---

## Linear (`sync_executor._linear_sync` + OAuth helpers)

| Call surface | Method | Request (Vector) | Depend-on / ingest assumptions | Primary docs | Mock parity |
|-------------|--------|-----------------|----------------------------------|--------------|-------------|
| OAuth token | `POST https://api.linear.app/oauth/token` | `application/x-www-form-urlencoded` authorization-code exchange (`linear/http_client.py`) | `{access_token, refresh_token?, expires_in?}` | [OAuth authentication](https://developers.linear.app/docs/oauth/authentication) | — prod endpoint |
| GraphQL viewer/org probe | `POST https://api.linear.app/graphql` | `{ query }` for nested viewer/org | `data.viewer.organization{id,name}` | Working with GraphQL | — prod endpoint (Docker workaround documented in settings) |
| GraphQL ingestion | `POST {linear_graphql_url()}` | JSON `{operationName, query, variables:{first, after}}` headers Bearer token | Each operation MUST expose typed connections `{nodes, pageInfo}` paths enumerated below | [Working with GraphQL](https://developers.linear.app/docs/graphql/working-with-the-graphql-api) | ✅ Named ops + cursor paging; fixture nodes align with `LINEAR_*_QUERY` selections (subset of full Linear schema) |
| Viewer ping | `POST {linear_graphql_url()}` | Body **`{ query }` only** — `query ViewerPing { viewer { id name } }` | `data.viewer.{id,name}` | Same | ✅ Fallback recognizes `ViewerPing` in query text when `operationName` absent |

Declared ingestion queries (`sync_executor.py`): **`LinearIngestIssues`**, **`LinearIngestComments`**, **`LinearIngestProjects`**, **`LinearIngestCycles`**, **`LinearIngestIssueRelations`**, **`LinearIngestIssueLabels`**, **`LinearIngestInitiatives`**, **`LinearIngestProjectUpdates`**, **`ViewerPing`**.

**Attachments**: `LinearIngestIssues` selects `attachments { nodes { id title url } }`; fixture/issues include sample attachment nodes where applicable.

Mock router (`backend/mock_connectors/linear_mock/server.py`): `/graphql` plus **`POST /oauth/token`** shim returning fixed bearer tokens.

---

## Calls connector — Google OAuth & Calendar (`calls/http_client.py` + `_calls_sync`)

| Call surface | Method | Request (Vector) | Depend-on / ingest assumptions | Primary docs | Mock parity |
|-------------|--------|-----------------|----------------------------------|--------------|-------------|
| OAuth token | `POST https://oauth2.googleapis.com/token` | Form fields authorization-code grant | `{access_token, refresh_token?, expires_in}` | [Token endpoint](https://developers.google.com/identity/protocols/oauth2/web-server#exchange-authorization-code) | — prod |
| Profile ping | `GET https://www.googleapis.com/oauth2/v3/userinfo` | Bearer token | `{sub, email}` preferred | [OpenID userinfo](https://developers.google.com/identity/protocols/oauth2/openid-connect#obtainuserinfo) | — prod |
| Calendar events | `GET /calendars/primary/events` | Query params **`singleEvents=true`**, **`maxResults`**, **`orderBy=updated`**, **`updatedMin`?, **`pageToken`?** | JSON **`kind`**, **`items`**, **`nextPageToken`**, event objects with **`updated`**, **`attendees`**, etc. | [events.list](https://developers.google.com/calendar/api/v3/reference/events/list) | ⚠️ **Envelope** matches Calendar list (`calendar#events`, `items`, paging). **`extendedProperties.private`** carries transcript/recording JSON under Vector-only keys — intentional bridge, not a Google-documented field |

Mock routing (`calls_mock/server.py`): prefixes **`/google-calendar/v3`**.

---

## Internal mock-only surfaces (non vendor parity targets)

| Mock-only endpoint | Purpose | Compliance verdict |
|--------------------|---------|-------------------|
| `GET /admin/dataset/full` | Hydrates mock connectors via bundled deterministic fixtures (`company_generator.py`). | **Mock-internal** — no vendor analogue |

---

## How to extend / certify drift control

1. When adding a new outbound connector poll: append rows above **before merging ingestion**.
2. For Slack/GitHub objects ingested into Cortex canonical envelopes: snapshot fixtures MUST expose whichever discriminator keys ingestion asserts (`reply_count` parity noted above).
3. Optional automation paths:
   - Contract-test mock routers against recorded golden vendor payloads (record/replay).
   - Diff declared GraphQL selections (`LINEAR_*_QUERY`) vs runtime field reads (`sync_executor` payload builders).

---

*Generated from repository inspection (`backend/src/vector/domains/cortex/connectors/**`, `sync_executor.py`, `mock_connectors/**`). Update when ingestion surfaces change.*
