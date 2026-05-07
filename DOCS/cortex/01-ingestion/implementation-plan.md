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

## Phase-Specific Implementation Blockers
- Connector auth model not finalized (OAuth secrets + install flows exist; ingestion-scoped auth semantics still tied to Phase 01 runtime).
- Raw envelope frozen-core doctrine not yet implemented in runtime validation.
- ~~Step 0 migration inventory~~ **Done** — Appendix A in `phase-01-step-0-connector-migration-safety-spec.md` (2026-05-07).
- ~~Step 0 migration flags (settings + routing policy)~~ **Done** — `CORTEX_CONNECTOR_MIGRATION_*`, `cortex_ingestion_policy`, admin enqueue stubs (2026-05-07). **Shadow/active dual execution and parity automation** still **Phase 01 Step 6+**.
