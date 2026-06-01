# Cortex Roadmap

## Strategic Sequence
1. Establish ingestion and raw memory guarantees.
2. Build canonical event model and deterministic mapping.
3. Resolve identities and construct execution graph (links).
4. **Declared Domains** — cross-tool rollups of declared work containers + momentum ([`declared-domains-v1-plan.md`](../declared-domains-v1-plan.md)).
5. Emergent Domains (future) and execution intelligence (future).
6. Introduce derived memory and temporal reasoning.
7. Add retrieval orchestration and synthesis interfaces.
8. Harden operations, governance, and lifecycle controls.

## Milestone View
- M1: Connector + raw-store baseline with replay safety.
- M2: Canonicalization and schema versioning live.
- M3: Cross-tool identity resolution and graph projection.
- M3.5: **Declared Domains** — deterministic scope rollups (V1 execution scope).
- M4: Memory derivation and reasoning artifacts.
- M5: Retrieval API and synthesis-ready context packs.
- M6: Admin, observability, and governance operations.

## Roadmap Rules
- No milestone advances without deterministic replay checks.
- Every phase must define testability and rollback strategy before implementation starts.
- Schema/version migration paths are mandatory for all persistent structures.
