# Phase 01 / Step 0 — Connector Migration Safety Spec

## Objective
Migrate existing connector logic to Cortex-owned ingestion boundaries safely, without breaking current app behavior (frontend, HTTP routes, backend jobs, or tenant connector operations).

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
- `cortex_connector_migration_enabled` (global default off).
- `cortex_connector_migration_<connector>` (connector-level control).
- `cortex_connector_migration_<connector>_tenants` (tenant cohort allowlist).
- Emergency kill switch routes traffic to legacy path immediately.

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

## Implementation Readiness Exit For Step 0
Step 0 is complete only when:
- inventory is complete and reviewed,
- compatibility gates are codified,
- feature flags and kill switch strategy are documented,
- rollback drill procedure is defined,
- first shadow rollout plan is approved.
