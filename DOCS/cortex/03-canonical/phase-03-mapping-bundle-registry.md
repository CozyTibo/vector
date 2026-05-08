# Phase 03 — Mapping Bundle Registry (Normative Specification)

**Status:** normative operational contract for the **mapping system**.  
**Anti-goal:** no semantic truth claims—only versioned structural transforms (`phase-03-anti-goals-doctrine.md`).

## Purpose

The registry is the **single authoritative inventory** of what “mapping version” means at runtime: which bundles exist, their compatibility, ownership, and how tenants pin versions during rebuild/remap.

## Core definitions

| Term | Definition |
| ---- | ---------- |
| **Mapping bundle** | Named, versioned set of artifacts: ontology slice, rule tables, parse grammars, field maps, per-connector micro-versions, logical-key derivation profile. |
| **Bundle ID** | Immutable identifier for an exact artifact hash set (e.g., `mb-2026.05.08.3`). |
| **Compatibility line** | Ordered sequence of bundle IDs declaring safe upgrade paths for replay-safe remapping (`phase-03-replay-versioning-doctrine.md`). |
| **Pin** | Tenant-scoped declaration that canonicalization for scope S uses bundle B until changed. |

## Registry records (minimum fields)

Each bundle entry SHALL document:

- **bundle_id**, **release_date**, **status** (`draft` | `candidate` | `active` | `deprecated` | `retired`),
- **artifact_hashes** (deterministic content addressing for each table artifact),
- **owner** (team + on-call), **approver** for promotion to `active`,
- **CHANGELOG** with mapping-level notes (not prose interpretation—structural deltas only),
- **compatibility**: prior bundle IDs this replaces/supersedes; breaking vs non-breaking flag,
- **scope defaults**: which connectors/resource types the bundle claims to cover (coverage matrix row).

## Ownership & governance

- **Owner:** accountable for correctness of deterministic transforms + registry hygiene.
- **Promotions:** `draft → candidate → active` require signed review checklist (determinism checklist, anti-goal scan).
- **Deprecation:** retired bundles remain addressable for historical rebuild attribution—never delete identifiers.

## Version pinning semantics

- Runtime canonicalization MUST record `mapping_bundle_id` on every emitted canonical row/provenance edge (`phase-03-transform-lineage-doctrine.md`).
- Rebuild jobs MUST declare intended bundle pin (or explicit “active head” policy with guardrails).

## Invalidation linkage

When bundle B supersedes A:

- Mark outputs produced under A as **superseded-by-bundle** per replay doctrine—never silent rewrite.

## References

- Logical keys: `phase-03-logical-key-doctrine.md`
- Transform lineage: `phase-03-transform-lineage-doctrine.md`
- Mapping system umbrella: `phase-03-mapping-system-doctrine.md`
