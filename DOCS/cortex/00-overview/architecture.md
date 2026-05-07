# Cortex High-Level Architecture

## Domain Isolation
Cortex implementation is strictly isolated under `backend/domains/cortex/`. Upstream systems may publish source data; they may not bypass Cortex contracts to write canonical or memory layers directly.

## Layer Contract Topology
1. `connectors` -> source fetch and envelope normalization.
2. `ingestion` -> validation and raw event persistence.
3. `raw_store` -> immutable source truth and replay index.
4. `canonical` -> tool-agnostic organizational event model.
5. `entity_resolution` -> cross-tool identity linkage.
6. `graph` -> temporal relation graph construction.
7. `memory` -> compressed and derived memory representations.
8. `reasoning` -> deterministic + bounded AI inference artifacts.
9. `retrieval` -> evidence-grounded query planning and context packs.
10. `synthesis` -> explainable narrative assembly from evidence.
11. `admin`/`observability` -> controls, replay operations, governance.

## Hard Architecture Boundaries
- No phase may write into non-adjacent downstream stores.
- All phase outputs must include `tenant_id`, `schema_version`, and `provenance`.
- Canonical and memory layers are append-oriented; corrections are represented as superseding records, not in-place semantic rewrites.
- AI cannot mutate raw or canonical facts; AI may produce inferred artifacts only.

## Trust Domains
- Raw domain: source-faithful evidence.
- Canonical domain: normalized organizational facts.
- Inference domain: confidence-scored interpretations.
- Interaction domain: synthesized outputs referencing evidence + inference.

## Cross-Tenant Safety
Every key and index must be tenant-scoped. Cross-tenant joins are forbidden unless explicitly defined for platform-level operations that never expose tenant payloads.

## Reference Documents
- Field semantics: `docs/cortex/schemas/field-semantics.md`
- Terminology policy: `docs/cortex/00-overview/terminology-consistency.md`
- Invariants: `docs/cortex/00-overview/architectural-invariants.md`
