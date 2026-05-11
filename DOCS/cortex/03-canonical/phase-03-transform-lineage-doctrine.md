# Phase 03 — Transform Lineage & Field Lineage Doctrine

**Status:** normative. Covers **how** mapping outputs explain themselves—not business meaning.

## Scope

This doctrine specifies **transform provenance** for every canonical field:

- Which rule/table populated it,
- Which raw paths were read,
- Which bundle version applied,
- How remap/rebuild must replay that derivation.

## Canonical field lineage (minimum)

Each populated canonical field MUST be attributable via:

- **`bundle_id`**, **`rule_id`** (or table row id), **`source_paths`** (JSON pointers into raw envelope),
- **`evidence_grade`** per deterministic doctrine (E0/E1),
- Optional **`ambiguity_ref`** when field is absent but contested alternatives exist.

## Transform provenance record (conceptual)

- **inputs:** enumerated raw record ids + cited paths,
- **transform:** deterministic function identifier + version,
- **outputs:** canonical logical key + emitted fields snapshot hash (canonical serialization per deterministic doctrine).

## Replay-safe remapping

When `bundle_id` changes from A→B on the same raw:

- Emit new canonical version rows under B with explicit **supersedes** pointers to A-era rows when semantics-equivalence holds; otherwise mark divergence class per replay doctrine (`C1`/`C2`).
- Never discard A-era lineage; tombstone + supersession only.

## Mapping invalidation semantics

Invalidation reasons are enumerable:

- `bundle_bump`, `raw_revision_append`, `trust_gate`, `schema_correction`, `operator_rebuild`.

Each invalidation event MUST be logged with scope + bundle pins.

## Compatibility expectations

- **Non-breaking bundle bump:** same logical keys for unchanged raw inputs; only additive fields or stricter validation allowed—proved via regression vectors.
- **Breaking bump:** requires compatibility line entry + migration plan + divergence expectation documented before activation.

## References

- Registry: `phase-03-mapping-bundle-registry.md`
- Logical keys: `phase-03-logical-key-doctrine.md`
- Provenance graph: `phase-03-provenance-traceability-doctrine.md`
