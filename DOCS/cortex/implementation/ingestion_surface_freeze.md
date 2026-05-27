# Ingestion surface freeze (Phase 4)

**Status:** normative guardrail  
**Parent:** [organizational_exhaust_implementation_plan.md](./organizational_exhaust_implementation_plan.md)

---

## Allowed runtime modules

New exhaust code **only** in:

- `backend/src/vector/domains/cortex/ingestion/connectors/*/sync.py`
- Small shared helpers: `sync_shared`, `checkpoint_contract`, `sync_context`, `live_idempotency`, `sync_router`, `scheduler`, `stream_checkpoint`, `worker_queue_roles_v1`
- Admin **read** paths: `admin_overview`, `admin_recent_raw`, `scheduler_tick_history`

Existing `raw_memory_*` governance stays; do not expand that surface for organizational exhaust.

---

## Forbidden in ingestion PRs

- Cross-provider identity / graph / canonicalization  
- Coverage ledger, debt planner, stream orchestrators  
- New Celery beat schedules beyond ingestion tick  
- Per-stream or per-tenant worker fleets  
- Ingestion-time “smart” prioritization engines  

Downstream domains consume `raw_ingestion_records` via SQL/API.

---

## Production evolution (allowed)

- New `resource_type` + checkpoint stream + matrix/registry row  
- `introduced_at` on ship  
- `ingestion_version.extraction` bump when payload shape changes (`live_idempotency`)  
- Operator `reset-stream` on live checkpoint scope  

No raw DELETE for schema evolution.
