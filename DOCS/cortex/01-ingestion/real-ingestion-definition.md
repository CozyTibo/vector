# Real Ingestion — Definition

**Authoritative Phase 01 exhaust spec:** `phase-01-organizational-exhaust-spec.md` (goal, exit criteria, pagination/cursor/replay rules, non-goals).  
**Raw row unit model:** `phase-01-raw-persistence-doctrine.md`.  
**Continuity (backfill vs incremental, idempotency, live/replay, convergence):** `phase-01-ingestion-continuity-doctrine.md`.  
**Live-lane idempotency closure doctrine:** `phase-01-live-idempotency-doctrine.md`.  
**Gap map + implementation roadmap:** `../implementation/organizational-exhaust-execution-track.md`.

**Real ingestion** means **continuous organizational exhaust acquisition** into Cortex raw storage: durable, checkpointed, replay-aware pulls of **meaningful operational signals**, not demos.

## Real ingestion **includes**

- **Full pagination** (or GraphQL cursor connections) until bounded completion or an **explicit, checkpoint-resumable** operator/tenant window
- **Per-stream checkpoint continuity** across failures and restarts (`connector_sync_state` scoped correctly, including **nested cursors**)
- **Historical backfill** where product policy requires past windows (with throttles and cost gates) — not “latest page only” without a continuation plan
- **Incremental synchronization** after backfill (same code paths where possible)
- **Replay-safe retrieval** for streams that participate in replay jobs (idempotency keys, envelope contracts)
- **Stable live logical idempotency + revision-safe append semantics** (no run-scoped live identity keys)
- **Large-scale persistence** to `raw_ingestion_records` with **exhaust-verifiable** admin views (counts, time span, resource mix)

## Real ingestion **excludes**

- **Shallow API validation** whose only purpose is to prove credentials
- **Ping rows** (`*.scope_ping`, `viewer_ping`) as the *dominant* or *sole* evidence of ingestion for a connected tool
- **First-page-only** or **fixed-N** fetches **without** cursor/checkpoint path to completeness
- **Ad-hoc** fetches that bypass run/checkpoint lifecycle

## Alignment with runtime

The codebase may implement **real ingestion for some resource types** and **not others**. That split must be **visible** in:

- `DOCS/cortex/connectors/connector-exhaust-matrix.md`
- `DOCS/cortex/implementation/organizational-exhaust-execution-track.md` (gap map)
- `DOCS/cortex/MASTER_TRACKER.md` — **Organizational Exhaust Coverage**
- Admin API `GET /admin/tenants/{tenant_id}/cortex/ingestion/exhaust-coverage`, `raw-stats`, and raw row browsing

**Phase 01 infrastructure steps 0–6** can be complete while **Phase 01 exhaust** remains **incomplete**. Exhaust closure follows **`phase-01-organizational-exhaust-spec.md` §11** **and** `phase-01-live-idempotency-doctrine.md`, not substrate or admin “health” alone.
