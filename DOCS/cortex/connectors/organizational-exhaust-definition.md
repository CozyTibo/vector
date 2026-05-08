# Organizational Exhaust — Definition

Cortex reconstructs organizations **through exhaust**: the durable, replayable stream of **what people and systems actually did** in tools (communication, coordination, review, delivery, ownership, operations).

## Exhaust categories (non-exhaustive)

| Category | Examples |
| -------- | -------- |
| **Communication exhaust** | Slack messages, threads, DMs (policy-bound), email handoffs where integrated |
| **Coordination exhaust** | Linear issues, projects, cycles, relations; Notion tasks / databases |
| **Review exhaust** | GitHub PRs, reviews, comments, checks |
| **Delivery exhaust** | Commits, deployments, workflow runs, build artifacts (metadata) |
| **Decision exhaust** | Issue state transitions, approvals, policy gates recorded in tools |
| **Ownership exhaust** | Assignees, teams, repos, initiatives, RACI-like signals |
| **Operational exhaust** | Incidents, alerts, on-call rotations (where connectors support them) |

## What exhaust is *not*

- One-off **connectivity pings** or **single-field API validation** rows used only to prove OAuth — those are *health signals*, not organizational exhaust.
- **First-page-only** fetches without a committed plan for **pagination, checkpoints, and historical backfill** — that is *partial exhaust at best*, not “full ingestion.”

## Relationship to phases

- **Phase 01 — Ingestion** must expand until it **continuously acquires** exhaust at the depth the product requires (per connector resource matrix).
- **Phase 02 — Raw Memory** makes that **large, append-only corpus** safe, queryable, retained, and replay-governed at scale.
- **Phase 03 — Canonicalization** maps exhaust into **canonical entities and relations** with provenance.

See also: **`../01-ingestion/phase-01-organizational-exhaust-spec.md`** (Phase 01 normative exhaust + exit criteria), `ingestion-depth-model.md`, `connector-exhaust-matrix.md`, `../01-ingestion/real-ingestion-definition.md`, `../implementation/connector-expansion-roadmap.md`, `../implementation/organizational-exhaust-execution-track.md`, `../MASTER_TRACKER.md` §2.5, and admin `GET …/cortex/ingestion/exhaust-coverage` + `GET …/cortex/ingestion/raw-stats`.
