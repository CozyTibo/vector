# Product onboarding (design partners)

## Purpose

First-run flow for early teams: create context (tenant already exists from sign-up), capture company + tool interest, connect GitHub, run one ingestion pass (Steps 1–3), then stop before insights UX.

Connector installs and sync remain the **existing** `/connectors/*` APIs; onboarding only tracks **step + answers** in `onboarding_state`.

## State machine (API + UI)

| Step | Meaning |
|------|---------|
| `WELCOME` | Intro |
| `COMPANY_INFO` | `company_name`, optional `company_domain` in `answers_json`; name also updates `tenants.company_name` |
| `TOOLS_SELECTION` | `tools_interest` string ids in `answers_json` (preferences only) |
| `CONNECT_GITHUB` | User hits `/connectors/github/install?return_to=/app/onboarding` |
| `SCANNING` | Frontend calls `POST /connectors/github/sync`, then `POST /onboarding/complete` |
| `THANK_YOU` | Shown when `status = completed` |

Statuses: `in_progress`, `completed`, `abandoned` (`abandoned_at` reserved for future drop-off handling).

## Database

Table **`onboarding_state`** (one row per tenant):

- `tenant_id` (unique FK → `tenants.id`)
- `status`, `current_step`
- `answers_json` (JSONB) — e.g. `{ "company_name", "company_domain", "tools_interest": ["github","linear"] }`
- `version`, timestamps: `created_at`, `updated_at`, `started_at`, `completed_at`, `abandoned_at`

**Not** stored here: OAuth tokens, installation ids, connections (`tenant_connections` stays source of truth).

## HTTP API (session cookie)

| Method | Path | Role |
|--------|------|------|
| `GET` | `/onboarding` | Create row on first access; return state + `github_connected` (derived) |
| `PATCH` | `/onboarding` | Update `current_step` and merge `answers` into `answers_json` |
| `POST` | `/onboarding/complete` | Mark `completed`, set `completed_at`, step `THANK_YOU` (idempotent if already completed) |

GitHub: `GET /connectors/github/install?return_to=...` embeds an optional app-only path (allowlisted under `/app/…`) in signed `state`; callback redirects to `{frontend}{return_to}?github_connected=1` or legacy `/?github_connected=1`.

## Analytics (lightweight)

From admin or SQL:

- **Time to complete**: `completed_at - started_at`
- **Drop-off**: rows `in_progress` with stale `updated_at`, or future `abandoned_at`

## Admin

- `GET /admin/tenants` — each item includes `onboarding_status`, `onboarding_current_step`, `connected_connectors`
- `GET /admin/tenants/{id}` — detail includes `onboarding` snapshot + connectors

## Frontend

Route: `/app/onboarding` — full-screen steps, persistence via `GET`/`PATCH`/`POST` above; thank-you CTA → `/app/connectors`. Raw ingestion inspection is **admin-only** (e.g. tenant **Step1 Raw**).

**Gate:** `GET /me` includes `onboarding_completed` (true only when `onboarding_state.status === completed`). While the field is present and not `true`, authenticated routes under `/app/*` redirect to `/app/onboarding` except when already on that path — so users cannot skip to Connectors via **App home** or **Google OAuth** (`/?oauth_ok=1` → `/app`) until they finish.

## Copy (shipping strings)

Tool-neutral welcome; no em dashes in UI strings.

- **Welcome:** “Let Vector learn how your team works.” Body stresses tools already tell how you ship; Vector learns from real activity across engineering, project, and communication tools.
- **Company:** “Who’s this workspace for?” Name + optional domain.
- **Tools:** “Which tools matter to you?” Preferences only. Trust line: sensitive tools (e.g. GitHub, Slack, Notion): no storage of code, messages, or documents; only execution signals.
- **GitHub:** “Connect GitHub”. Today GitHub syncs engineering activity; install app for workspace.
- **Scanning:** “We’re syncing your workspace”. Rotating generic progress lines (not repo/PR specific).
- **Thank you:** “You’re early. We’re learning with you.” Processing activity from connected tools; design partners.
