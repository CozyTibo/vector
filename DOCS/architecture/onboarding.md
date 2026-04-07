# Product onboarding (design partners)

## Purpose

First-run flow for early teams: capture company context and **which tools the team uses**, connect **Slack** (or acknowledge Teams/Discord placeholder) in-product, then mark onboarding complete. Linear, GitHub, and other tools are **not** wired during this flow; users add them from **Connectors** later.

Connector installs use the existing `/connectors/*` APIs; onboarding tracks **step + answers** in `onboarding_state`.

## State machine (API + UI)

| Step | Meaning |
|------|---------|
| `CHAT_PROFILE` | Chat-first profile (phases in `answers_json.profile_phase`, including tool picker) |
| `CONNECT_COMMUNICATION` | Slack OAuth and/or Teams+Discord placeholder; order from `connect_queue` |
| `SCANNING` | Legacy mid-flow state; clients should call `POST /onboarding/complete` and show thank-you |
| `THANK_YOU` | Shown when `status = completed` |

Statuses: `in_progress`, `completed`, `abandoned` (`abandoned_at` reserved for future drop-off handling).

## Database

Table **`onboarding_state`** (one row per tenant):

- `tenant_id` (unique FK → `tenants.id`)
- `status`, `current_step`
- `answers_json` (JSONB) — e.g. profile, `tools`, `connect_queue`, `tools_interest`
- `version`, timestamps: `created_at`, `updated_at`, `started_at`, `completed_at`, `abandoned_at`

**Not** stored here: OAuth tokens, installation ids, connections (connector tables stay source of truth).

On load, rows that still have removed step ids (`CONNECT_GITHUB`, `CONNECT_LINEAR`) or stale `connect_queue` entries for those tools are **normalized** in the onboarding repository before use.

## HTTP API (session cookie)

| Method | Path | Role |
|--------|------|------|
| `GET` | `/onboarding` | Create row on first access; return state + `github_connected`, `linear_connected`, `slack_connected` (derived) |
| `PATCH` | `/onboarding` | Update `current_step` and merge `answers` into `answers_json` |
| `POST` | `/onboarding/complete` | Mark `completed`, set `completed_at`, step `THANK_YOU` (idempotent if already completed) |

OAuth callbacks may append `?github_connected=1`, `?linear_connected=1`, or `?slack_connected=1` to `return_to`; the onboarding UI refreshes state from these flags where relevant.

## Analytics (lightweight)

From admin or SQL:

- **Time to complete**: `completed_at - started_at`
- **Drop-off**: rows `in_progress` with stale `updated_at`, or future `abandoned_at`

## Admin

- `GET /admin/tenants` — each item includes `onboarding_status`, `onboarding_current_step`, `connected_connectors`
- `GET /admin/tenants/{id}` — detail includes `onboarding` snapshot + connectors

## Frontend

Route: `/app/onboarding` — chat + tool picker + communication connect card; thank-you CTA → `/app/connectors`.

**Gate:** `GET /me` includes `onboarding_completed` (true only when `onboarding_state.status === completed`). While the field is present and not `true`, authenticated routes under `/app/*` redirect to `/app/onboarding` except when already on that path.

## Copy (shipping strings)

Tool-neutral welcome; no em dashes in UI strings.

- **Tools:** Preferences across communication, engineering, PM, docs; trust line on sensitive tools.
- **Slack / Teams / Discord:** Communication step only; other tools from Connectors after onboarding.
- **Thank you:** “You’re early. We’re learning with you.” Processing activity from connected tools; design partners.
