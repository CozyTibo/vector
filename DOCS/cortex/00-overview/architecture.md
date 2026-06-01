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
7. `declared_domains` -> cross-tool rollups of declared work containers (initiative/project seeds) with momentum. **V1 execution-scope layer.** See [`declared-domains-v1-plan.md`](../declared-domains-v1-plan.md).
8. `memory` -> compressed and derived memory representations.
9. `reasoning` -> deterministic + bounded AI inference artifacts.
10. `retrieval` -> evidence-grounded query planning and context packs.
11. `synthesis` -> explainable narrative assembly from evidence.
12. `admin`/`observability` -> controls, replay operations, governance.

**Future (not in layer topology yet):** `emergent_domains` — hybrid materialization of undeclared concerns; **sibling** to `declared_domains`. **Execution Intelligence** consumes scope layers; it is not a materialization layer.

**Deprecated naming:** `topic materialization`, `declared work rollup`, `execution domain` (V1) — use **Declared Domain**.

## Execution Surfaces (first product consumer)

**Execution Surfaces** are a **read-only composition layer** over substrate outputs (canon, identity, graph, declared domains). They are the first human-facing execution-reality consumer — not a new pass, scheduler, or store.

- **Admin V1 plan:** [`execution-surfaces-v1-admin-plan.md`](../execution-surfaces-v1-admin-plan.md)
- **Substrate tabs** (Ingestion, Canon, Identities, Declared Domains ops, Links) remain operator/debug views.
- **Execution Intelligence** (future) interprets scope; surfaces show state only.

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
