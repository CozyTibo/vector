# Phase 01 / Step 0 — Connector Migration Safety Spec

## Objective
Migrate existing connector logic to Cortex-owned ingestion boundaries safely, without breaking current app behavior (frontend, HTTP routes, backend jobs, or tenant connector operations).

**What “move to Cortex” means at Step 0:** put connector adapter/runtime code in **one** canonical package — `vector.domains.cortex.connectors` (filesystem `domains/cortex/connectors/`) — so Step 1 does not repeat a package shuffle or maintain two connector trees. That consolidation sits alongside **Cortex ingestion routing** (env flags, policy module, future worker dispatch hooks).

## Non-Negotiable Outcomes
- Existing connector-facing product behavior remains stable during migration.
- Existing API routes and response contracts remain backward-compatible during cutover.
- No tenant-wide ingestion outage from migration rollout.
- Fast rollback path exists for every migration slice.

## In-Scope Components
- Existing connector adapter/runtime logic in current domains.
- Connector-related API handlers and service entry points.
- Queue/worker dispatch paths used by connector sync and recovery.
- Admin connector controls and status visibility surfaces.

## Out-Of-Scope
- Canonical/identity/reasoning semantics changes.
- Connector feature expansion unrelated to migration safety.
- Frontend redesign beyond compatibility updates.

## Migration Strategy (Compatibility-First)
1. **Inventory + Contract Freeze**
   - Enumerate all connector entrypoints (routes, jobs, services, admin actions).
   - Freeze external contracts used by frontend and API consumers for migration window.
2. **Boundary Adapter Layer**
   - Introduce compatibility adapter so old call sites can invoke Cortex ingestion entrypoints without route/UI changes.
   - Keep request/response shape unchanged at external boundaries.
3. **Dual-Path Runtime (Shadow Then Active)**
   - Shadow mode: Cortex path executes with no side-effect publication, compare outputs/metrics.
   - Active mode: enable Cortex path per connector/tenant behind feature flag.
4. **Progressive Cutover**
   - Cutover by connector, then by tenant cohorts.
   - Start with low-blast connectors, then high-volume connectors.
5. **Legacy Path Decommission**
   - Remove old connector execution path only after parity gates are stable for defined soak period.

## Feature Flags And Control
- `cortex_connector_migration_enabled` (global default **on** in application settings; set `false` to disable).
- `cortex_connector_migration_<connector>` (per-connector default **on**; set `false` to disable that connector).
- `cortex_connector_migration_<connector>_tenants` (tenant cohort allowlist; empty = all tenants).
- Emergency kill switch: set master or per-connector flags to `false` in environment / config.

**Runtime (Vector codebase):** Environment variables `CORTEX_CONNECTOR_MIGRATION_*` map to `Settings` fields; routing uses `vector.domains.cortex.connectors.cortex_ingestion_policy` and `Settings.cortex_migration_route_active`. Admin enqueue shims (`connector_sync.enqueue_*`) raise `NotImplementedError` when the Cortex path is selected for a tenant but the executor is not wired yet.

## Backward-Compatibility Requirements
### API / Routes
- Preserve route paths, auth model, payload schema, and status semantics.
- If new fields are needed, add optional fields only.

### Backend / Worker
- Preserve queue contract compatibility for existing producers/consumers during transition.
- No breaking change in retry/dead-letter semantics without migration gate.

### Frontend / Admin
- Existing connector status and action surfaces remain functional.
- New CTA behavior (`Scheduled Polling`, `Trigger Connector Ingestion`) must map cleanly onto migration flags and queue state.

## Non-Breakage Validation Gates
| Gate | Validation | Required For |
| ---- | ---------- | ------------ |
| Contract parity | Legacy vs Cortex route contract parity checks pass | Shadow -> Active |
| Ingestion parity | Envelope/idempotency/checkpoint behavior matches expected bounds | Connector cutover |
| Operational parity | Retry, dead-letter, throttling behavior within accepted variance | Tenant cohort expansion |
| Admin parity | Connector controls/status UI remains correct | Full connector migration |
| Rollback drill | Kill switch rollback validated in staging | Production rollout |

## Observability Requirements During Migration
- Per connector: legacy path vs Cortex path success/failure rates.
- Queue depth, retry rate, dead-letter rate by path.
- Checkpoint progression lag by connector + tenant.
- Route-level latency/error regression alerts.
- Admin action audit trail for migration toggles and manual ingestion triggers.

## Rollback Strategy
### Immediate Rollback (Minutes)
- Disable connector/tenant migration flag.
- Route new runs to legacy path.
- Keep Cortex artifacts as audit/debug data only.

### Controlled Recovery (Hours)
- Analyze parity deltas and failure class.
- Patch migration adapter or contract mapping.
- Re-enter shadow mode before reactivating cutover.

## Slice Plan (Execution Order)
0. Migration inventory, contract freeze, compatibility test matrix.
1. Build compatibility adapter and shadow execution hooks.
2. Run shadow parity for one connector + internal tenants.
3. Enable active mode for low-risk connector cohort.
4. Expand connector-by-connector with rollout gates.
5. Complete legacy path decommission and cleanup.

## Repository baseline (Vector, 2026-05-07)

- **Connector OAuth/install/disconnect** for `calls`, `github`, `linear`, `notion`, `slack` is implemented and forms the **primary external contract** to preserve during Phase 01.
- **Scheduled ingestion poll workers** that previously enqueued from admin **were removed**; admin exposes **stub** enqueue functions that raise. Phase 01 therefore introduces ingestion **execution** largely as **net-new** wiring into existing connections and persistence contracts—not a live “shadow vs legacy worker” dual path until a replacement worker ships.
- **Mock connectors** (`VECTOR_USE_MOCK_CONNECTORS` in `development` only) remain the local parity surface; production uses real provider APIs.

When dual-path (shadow/active) is implemented, apply **Migration Strategy** below; until then, **rollback** means **disable migration flags**, **stop enqueueing ingestion**, and **stabilize**—there is **no legacy poll worker** to fall back to until the replacement executor ships (connectors can stay OAuth-connected while freshness stalls).

## Appendix A — Codebase inventory (Step 0 snapshot)

**Purpose:** What exists today, what must stay stable, where Phase 01 runtime attaches.

### Executive baseline

| Fact | Implication |
| --- | --- |
| OAuth / install / disconnect live for five providers | Routes and response shapes are compatibility-critical. |
| Legacy Celery poll-sync enqueue **removed** (admin shims raise) | No parallel legacy worker to dual-run; Phase 01 adds **net-new** execution. |
| DB migrations include ingestion tables (`ingestion_runs`, `raw_ingestion_records`, …) | Align writers with frozen contracts in `01-ingestion/*schema*.md`. |
| Mock connectors dev-only (`VECTOR_USE_MOCK_CONNECTORS`, `ENV=development`) | Parity gates cover mock + real APIs where applicable. |

### HTTP surface (preserve)

| Method | Path | Role |
| --- | --- | --- |
| GET | `/connectors` | List connector status |
| POST | `/connectors/install/prepare` | Install ticket for SPA OAuth |
| DELETE | `/connectors/{provider_id}` | Disconnect |

Provider mounts: `/connectors/github|linear|notion|calls|slack`. **Slack:** `GET /slack/callback` at app root (`SLACK_CALLBACK_URL`). Contracts: `vector.contracts.connectors`.

### Domain

- Registry: `vector.domains.cortex.connectors.runtime` → adapters `calls`, `github`, `linear`, `notion`, `slack`.
- Ingestion workers should resolve connector type through this registry (or a successor facade).

### Admin / workers

- Admin: `vector.api.http.routes.admin` (lifecycle, OAuth starts, reset/delete).
- `connector_sync.enqueue_*`: stubs; when Cortex path selected → `NotImplementedError` until executor exists.
- Celery: email/onboarding today; future ingestion tasks register per `orchestration-model.md`.
- Logs: `vector.infrastructure.observability.ingestion_tasks.log_ingestion_event` when tasks exist.

### Env: migration flags (implemented)

| Variable | Role |
| --- | --- |
| `CORTEX_CONNECTOR_MIGRATION_ENABLED` | Master switch |
| `CORTEX_CONNECTOR_MIGRATION_CALLS` / `_GITHUB` / `_LINEAR` / `_NOTION` / `_SLACK` | Per-connector path |
| `CORTEX_CONNECTOR_MIGRATION_<CONNECTOR>_TENANTS` | Optional comma-separated tenant UUIDs; empty = all |

Routing: `vector.domains.cortex.connectors.cortex_ingestion_policy` + `Settings.cortex_migration_route_active`.

### Other

- DB / alembic: Step 1 ingestion migrations; tenant data via `tenant_connections`.
- Frontend: preserve list / install / OAuth / disconnect flows.
- Mock stack: `backend/mock_connectors/` (local dev).

Update this appendix when routes, providers, or queue wiring change.

## Appendix B — Rollback drill procedure

**Objectives:** Disabling Cortex routing restores safe behavior quickly; observability shows path when dual-path exists; rolled-back runs stop **new** bad writes (append-only raw history retained).

**Immediate rollback (minutes):** Turn off migration flags for affected scope; drain/cancel in-flight Cortex tasks for that scope; do not delete DB rows; alert if production impact.

**Controlled recovery (hours):** Parity delta → root cause → patch → shadow mode (when implemented) → active only after gates pass.

**Codebase caveat:** Until a **production ingestion executor** exists, rollback is **stop tasks + stop enqueueing**—not “flip to legacy worker.” Connectors may stay connected; **freshness** may stall until restored.

**Staging drill (when executor exists):** One low-risk connector + internal tenant → bounded sync → simulate failure (flag off or crash) → confirm no retry storm; document times.

**Drill approved when:** Kill switch exercised in staging post-executor; owner assigned.

## Implementation Readiness Exit For Step 0
Step 0 is complete only when:
- connector runtime/adapters live only under **`vector.domains.cortex.connectors`** (no parallel `vector.domains.connectors` tree),
- inventory and rollback procedure are captured (**this document — Appendix A/B**),
- compatibility gates are codified (gates table + Appendix A contract scope),
- feature flags and kill-switch behavior are documented (**§ Feature Flags** + env table in Appendix A),
- first shadow rollout plan is approved (**pending** — requires ingestion executor).

**Step 0 runtime scaffolding (flags + policy + package location):** `vector/settings.py`, `vector/domains/cortex/connectors/` (including `cortex_ingestion_policy.py`), admin `connector_sync` stubs. **Ingestion executor / shadow-active dual path:** Phase 01 Step 6+.
