# Local mock connectors & fixture dataset — strategy

**Status:** Implemented — see `backend/mock_connectors/README.md`.  
**Scope:** **Local development only.** A mock API (GitHub REST + Linear OAuth/GraphQL) and a rich fictional dataset. **Production, CI, and AWS always use real vendor APIs.**

---

## 1. Goals

- Run **Vector** locally against **deterministic, rich** GitHub + Linear data (multi-repo, multi-team, messy reality).
- **Never** enable mock connectors in **CI**, **staging**, **production**, or **AWS** — enforced by configuration validation and startup guards.
- Anchor **synthetic data** in one company story: mission → product → teams → projects → epics → work items → **optional** GitHub activity (PRs/commits) that **sometimes** aligns and **often** does not.

---

## 2. Environment model: local mock vs everything else

| Environment | GitHub / Linear | Mock server |
|-------------|-----------------|-------------|
| **Local dev (`ENV=development`)** | Optional: mock **or** real APIs via `VECTOR_USE_MOCK_CONNECTORS` | **Only when mock flag is true** — binds to **127.0.0.1** |
| **CI** | **Real APIs only**; `VECTOR_USE_MOCK_CONNECTORS=false` (mandatory) | **Must not** start |
| **Staging / Production / AWS** | **Real** `https://api.github.com` and `https://api.linear.app` | **Disabled** — startup guard asserts mock is off |

**Rules**

- Mock server **binds to loopback only** (`127.0.0.1`), never `0.0.0.0`.
- **Mock connectors are not a CI feature** — no deterministic “mock CI” mode; tests must not start mock servers.
- **No** production feature flag for mock URLs.

---

## 3. Switching: mock ↔ real (local)

### 3.1 Environment variables

- **`VECTOR_USE_MOCK_CONNECTORS`** — `true` only when `ENV=development`.
- **`VECTOR_MOCK_CONNECTOR_BASE_URL`** — e.g. `http://127.0.0.1:9183` (GitHub REST + Linear OAuth/GraphQL under this host).
- **`VECTOR_MOCK_SEED`** — deterministic dataset seed (default `42`).

When `VECTOR_USE_MOCK_CONNECTORS=true`, GitHub REST and Linear OAuth/GraphQL URLs point at the mock base. When `false`, defaults are `https://api.github.com` and `https://api.linear.app` (with Linear paths as implemented in settings).

**GitHub App installation tokens** — mock implements **`POST /app/installations/{id}/access_tokens`** and returns a **mock installation token** accepted by the mock GitHub REST routes.

### 3.2 Frontend admin: localhost-only toggle (optional, future)

- Only on `localhost` / `127.0.0.1`; server-side **env** remains authoritative.

---

## 4. Company narrative (fixture spine)

**Name:** Nexora — B2B SaaS, Series A.

### 4.1 Goal (mission)

- **Mission:** Help mid-market teams ship **reliable product changes** with **clear ownership** and **traceable execution**.

### 4.2 Product

- **“Nexora Workspace”** — multi-tenant web app + public API + mobile companion.
- **Multi-repo / multi-service:** separate repos per service (API, web, mobile, infra, integrations, data).

### 4.3 Teams (each owns a slice of the product)

| Team | Focus | Typical repos |
|------|--------|----------------|
| **Core API** | Domain, tenancy, auth | `nexora/api`, `nexora/auth-service` |
| **Web** | SPA, design system | `nexora/web`, `nexora/design-tokens` |
| **Mobile** | Clients | `nexora/mobile` |
| **Platform / Infra** | CI/CD, k8s | `nexora/infra`, `nexora/deploy` |
| **Integrations** | Connectors | `nexora/integrations`, `nexora/webhook-relay` |
| **Data** | Pipelines | `nexora/data-pipeline` |

### 4.4 Work hierarchy (Linear)

Initiative → Project → Epic → Issue → sub-issues; cycles optional; messy backlog.

### 4.5 GitHub (multi-repo)

Multiple repos, draft/stale PRs, keys in titles **sometimes**.

---

## 5. Named users (managers)

- **`thibault.hagler@gmail.com`** — EM; heavy Linear usage.
- **`victoire.charlet@edu.escp.eu`** — Product/engineering leadership; roadmaps, ETAs, initiatives.

---

## 6. Data hygiene scenarios

See §11 for graph-oriented patterns. Includes mis-linked GH↔Linear, tickets without descriptions, ETA threads, duplicate metadata, etc.

---

## 7. API coverage

- **GitHub:** Routes used by poll ingestion (`/installation/repositories`, pulls, pull commits, issues, commits; `POST` installation token).
- **Linear:** OAuth token + GraphQL (`viewer`, issues, teams, projects, comments, etc.) as implemented in the mock.

---

## 8. Documentation & handoff

- **`backend/mock_connectors/README.md`** — how to run mocks and the backend.

---

## 9. Implementation order

1. Env contract + safety guards.
2. Configurable GitHub/Linear URLs.
3. Mock server + deterministic dataset.
4. Validation script + Makefile.

---

## 10. Changelog

| Date | Change |
|------|--------|
| 2026-04-01 | Initial strategy. |
| 2026-04-01 | Added §11–§16; CI/AWS/local-only rules; implementation reference. |

---

## 11. Graph coverage targets

Execution patterns the dataset **must** instantiate (at least once each) so **Step 4** graph features can be tested.

| Pattern | Example | Why |
|---------|---------|-----|
| **Cross-tool dependency** | Linear issue blocked by / linked to GitHub PR | Core execution signal across tools |
| **Review bottleneck** | PR ready but waiting for review **>24h** | Delivery slowdown |
| **Untracked work** | PR opened **without** a Linear ticket | Execution hygiene |
| **Misaligned completion** | PR merged but ticket still open (or ticket closed before merge) | Workflow drift |
| **Cross-team dependency** | Team A issue blocked by Team B PR | Org coordination |
| **Duplicate work** | Two issues mapped to one PR (or duplicate issues) | Noise detection |
| **Stale epic** | All child issues closed but epic still open | Planning drift |
| **Discussion drift** | Slack thread **without** a Linear ticket | Signal gap (see §11.1) |
| **Abandoned branch** | PR inactive **>7 days** | Execution stall |
| **Multi-repo change** | One issue → PRs in **multiple** repos | Coordination complexity |

### 11.1 Slack (local fixture only)

- **Slack** is modeled as **synthetic events** in the dataset JSON (`slack_events` / thread metadata) for validation and future ingestion — **not** the Slack API. This satisfies “discussion without ticket” for graph testing without a Slack connector.

### 11.2 Graph structures to materialize

The dataset must produce subgraphs that map to:

- **Actor → Issue → PR → Repository**
- **Issue → blocks → Issue** (and epic ↔ epic where modeled)
- **Issue → Epic → Project** (and Initiative where present)
- **Actor → Comment → Issue**
- **PR → Commit** and **PR → Repository**
- **Issue ↔ PR** cross-tool edges (explicit, fuzzy, or missing — multiple variants)

---

## 12. Temporal simulation

Mock data **must** use **realistic timestamps** over a **30–90 day** window (UTC).

- Vector execution signals depend on **time** (staleness, review time, burstiness).
- **Examples** of intended sequences (illustrative):

| Day | Event |
|-----|--------|
| 1 | Ticket created |
| 3 | PR opened |
| 4 | Slack discussion (fixture) |
| 7 | Review requested |
| 9 | PR merged |
| 12 | Ticket closed |

**Required patterns:**

- Delayed reviews (large gap between “ready” and first review).
- Inactive PRs (no commits / no activity for **>7 days**).
- Tickets closed **after** PR merge vs **before** merge (misalignment).
- Bursts of commits vs idle periods.
- PRs with **>24h** wait in “review requested” state.

---

## 13. Identity reconciliation scenarios

Explicit cases for **actor** resolution (GitHub login, commit email, Linear user email):

| Case | Example |
|------|---------|
| GitHub login matches Linear user | Same **email** on both |
| GitHub login ≠ Linear email | **Alias** / different primary address |
| Commit email ≠ GitHub user email | `git config` mismatch / old employer |
| Multiple identities for one actor | Bot + human **or** service account |
| Actor missing in one system | Slack-only **or** Linear-only |

**Concrete example (must appear in dataset):**

- GitHub login: `thagler`
- Commit author email: `thibault@oldcompany.com`
- Linear email: `thibault.hagler@gmail.com`

This exercises **actor_external_identity** / merge logic.

---

## 14. Dataset scale

Target **baseline** (approximate; generator aims for these orders of magnitude):

| Entity | Target |
|--------|--------|
| Repositories | 8 |
| Users | 15 |
| Teams | 6 |
| Projects | 8 |
| Epics | 30 |
| Issues | 200 |
| PRs | 120 |
| Commits | 800 |
| Comments | 500 |
| Relationships (edges) | ~2000 |

Large enough for **graph traversal** and **signal** tests; exact counts may vary slightly by seed.

---

## 15. Dataset generator

- Generation is **deterministic**:
  - **`VECTOR_MOCK_SEED`** (e.g. `42`) — same seed → **identical** dataset.
- Benefits: reproducible bugs, stable local tests, **optional** export to JSON for inspection.

---

## 16. Dataset validation script

**Path:** `backend/mock_connectors/scripts/validate_mock_dataset.py` (run with `PYTHONPATH=backend/src:backend` or `make -f Makefile.mock mock-validate`).

**Checks (non-exhaustive):**

- No orphan artifacts (repos referenced by PRs exist; PRs reference valid repos).
- PRs link to repositories.
- Actor identities valid (emails, logins present where required).
- Timestamps **chronological** per entity where applicable (e.g. created ≤ merged ≤ closed).
- Dependency **loops** allowed but **flagged** (warning, not hard failure).
- Linear issue keys (`NEX-###`) referenced consistently **where** linkage is intended.

---

## 17. Safety requirements (summary)

| Guard | Behavior |
|-------|----------|
| **ENV** | `VECTOR_USE_MOCK_CONNECTORS=true` **only** if `ENV=development` |
| **Staging / production** | Assert mock connectors **off** at startup |
| **CI** | `VECTOR_USE_MOCK_CONNECTORS=false`; mock processes **must not** start in test pipelines |
| **Bind address** | Mock HTTP server **127.0.0.1** only |

---

## 18. Canonical filename

This document is the strategy reference: **`DOCS/strategy/local-mock-connectors-and-fixtures.md`**.

Legacy copy: `local-mock-connectors-and-dataset.md` may redirect here or be removed.
