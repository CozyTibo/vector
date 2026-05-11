# Connector & Ingestion Layer Implementation Plan

## Readiness Tracking
- Conceptual readiness: **Required** (phase boundaries signed off).
- Schema readiness: **Required** (input/output contracts frozen for slice).
- Infrastructure readiness: **Required** (storage, queues, observability prerequisites known).
- Dependency readiness: **Required** (upstream contracts stable).
- Unresolved architecture questions: **Must be explicitly listed and accepted**.
- Implementation blockers: **Must be empty before coding starts**.

## Sequencing
0. Execute connector migration safety step (`phase-01-step-0-connector-migration-safety-spec.md`).
1. Freeze contracts and invariants.
2. Define deterministic transformation algorithm.
3. Define failure classes and replay behavior.
4. Define observability and operator controls.
5. Execute implementation only after readiness gates pass.

## Exit Criteria
- Phase output contract conformance is testable.
- Replay behavior for this phase is documented and verifiable.
- Boundary violations have explicit guard checks.
- **Step 6 admin closure:** Phase 01 is not closed until the **Terminal step — admin & operator closure** gate in `DOCS/cortex/MASTER_TRACKER.md` is satisfied (ingestion-specific health, triggers, verification in the control plane).
- **Organizational exhaust (Phase 01 real closure):** Step 6 substrate closure **does not** close Phase 01. Exhaust closure is defined in **`phase-01-organizational-exhaust-spec.md`** (exit criteria) and executed per **`../implementation/organizational-exhaust-execution-track.md`**; final closure gate is Step **16** (`phase-01-runtime-correctness-hardening-doctrine.md`) after Step 15 logical idempotency lock. Track progress in `MASTER_TRACKER.md` §2.5, `connector-exhaust-matrix.md`, `connector-expansion-roadmap.md`, admin `exhaust-coverage` + raw aggregates. See `real-ingestion-definition.md`.
- **Runtime correctness lock (Phase 01 final gate):** Phase 01 is not closed without Step 16 requirements from `phase-01-runtime-correctness-hardening-doctrine.md` (concurrency/retry/crash correctness validation, checkpoint/cursor integrity, replay/live overlap validation, live dedupe validation, and finalized connection-scoping semantics).

## Admin closure (Step 6 gate)
Step **6** must ship operator-grade UI (or extend the internal admin app) so an operator can **see** ingestion state (runs, checkpoints, lag, failures, replay jobs), **trigger** scoped safe actions (e.g. manual sync, replay with preview), and **verify** end-to-end health against the phase checklist. Align layout and CTAs with `10-admin/phase-visualization-model.md` § Phase 01.

## Phase-Specific Implementation Blockers
- Connector auth model not finalized (OAuth secrets + install flows exist; ingestion-scoped auth semantics still tied to Phase 01 runtime).
- ~~Raw envelope frozen-core runtime validation~~ **Done** (Step 4 `raw_envelope_contract` + executor); extended probes remain Step 5+.
- ~~Step 0 migration inventory~~ **Done** — Appendix A in `phase-01-step-0-connector-migration-safety-spec.md` (2026-05-07).
- ~~Step 0 migration flags (settings + routing policy)~~ **Done** — `CORTEX_CONNECTOR_MIGRATION_*`, `cortex_ingestion_policy`, admin enqueue stubs (2026-05-07). **Shadow/active dual execution and parity automation** still **Phase 01 Step 6+**.
- ~~Phase 01 Step 1 ingestion lifecycle (minimal runtime)~~ **Done** — tables `ingestion_runs` / `raw_ingestion_records` / `connector_sync_state` (migration `20260508_0030`), domain `vector.domains.cortex.ingestion.sync_executor`, Celery `vector.cortex.ingestion.run_sync`, admin enqueue dispatches task when migration flags route the tenant.
- ~~Phase 01 Step 2 polling/orchestration~~ **Done** — Celery Beat `vector.cortex.ingestion.scheduler_tick`, `cortex_live` queue for `vector.cortex.ingestion.run_sync`, `vector.domains.cortex.ingestion.scheduler` + settings `CORTEX_INGESTION_SCHEDULER_*` / `CORTEX_INGESTION_MIN_GAP_SECONDS` (see `DOCS/cortex/MASTER_TRACKER.md`).
- ~~Phase 01 Step 3 replay-safe ingestion~~ **Done** — `IngestionSyncContext`, live vs `replay:<job_id>` checkpoint scopes, raw row replay lineage + idempotent replay inserts (migration `20260508_0031`), Celery `vector.cortex.ingestion.run_sync_replay` + `cortex_replay` queue, admin replay enqueue.
- ~~Phase 01 Step 4 persistence contracts~~ **Done** — `raw_envelope_contract` + `checkpoint_contract`, `sync_mode` allowlist, pre-persist envelope validation, monotonic checkpoint merge (`MASTER_TRACKER.md`).
- ~~Phase 01 Step 5 verification model~~ **Done** — `vector.domains.cortex.ingestion.verification`, post-sync verification in `sync_executor` when `CORTEX_INGESTION_VERIFY_AFTER_SYNC`, Celery `vector.cortex.ingestion.verify_tenant`, admin `connector_sync.verify_ingestion_invariants`, `PHASE_STEP5` / `ingestion_tasks` (`MASTER_TRACKER.md`).
- ~~Phase 01 Step 6 runtime + admin closure~~ **Done** — `admin_overview` + `cortex_scheduler_pause`, admin routes `/admin/tenants/{id}/cortex/ingestion` (+ verification, trigger-sync, trigger-replay), global `POST /admin/cortex/ingestion/scheduler-pause`, SPA **Cortex ingestion** tab, `PHASE_STEP6`, Beat respects Redis key `vector:cortex_ingestion:scheduler_paused`, full `connector_sync` enqueue shims (`MASTER_TRACKER.md`). **Follow-on:** live shadow/active soak and rollout sign-off.
