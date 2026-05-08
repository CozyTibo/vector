# Phase 03 — Mapping System Doctrine (Runtime Responsibility)

**Status:** normative umbrella for the **mapping subsystem**—independent from replay engine, ambiguity engine, and verification engine.

## Mission

Provide a **deterministic, versioned, auditable** path from Phase 02 raw records to canonical projections **without** collapsing independent runtime concerns into one pass.

## Components (runtime responsibilities)

| Component | Owns | Must not own |
| --------- | ---- | ------------ |
| **Registry** | Bundle IDs, pins, compatibility lines, ownership | Semantic judgments |
| **Logical key derivation** | Stable idempotency tuples per class | Cross-provider identity merges |
| **Rule engine** | Apply mapping tables / deterministic parsers | LLM classification |
| **Transform lineage** | Per-field provenance, remap explanations | Executive narrative |
| **Invalidation hooks** | Declare stale projections when bundles/raw/trust change | Silent deletes |

## Determinism guarantees

- Same inputs + same `bundle_id` + same engine version ⇒ identical logical keys + identical emitted canonical field snapshot hashes (subject to explicit normalization tables).
- No wall-clock dependence inside derivation functions.

## Integration boundaries

- **Upstream:** Phase 02 raw memory + trust signals.
- **Downstream:** ambiguity persistence (unresolved rule gaps), provenance graph writer, temporal ordering layer, query indexes.

## Operational interfaces (conceptual)

- `resolve_bundle_pin(tenant, scope) -> bundle_id`
- `materialize_canonical_slice(raw_cursor, bundle_id) -> canonical_ops + ambiguities + lineage_edges`
- `explain_field(canonical_row_id, field) -> transform lineage record`

## Failure isolation

Mapping failures produce **mapping-scoped** degraded states—never bypass ambiguity doctrine by injecting defaults that look like facts.

## References

- `phase-03-mapping-bundle-registry.md`
- `phase-03-logical-key-doctrine.md`
- `phase-03-transform-lineage-doctrine.md`
- `phase-03-deterministic-canonicalization-doctrine.md`
