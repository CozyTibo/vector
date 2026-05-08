# Phase 03 — Replay, Rebuild, Versioning & Canonical Idempotency Doctrine

**Status:** normative. Supersedes informal `canonicalization-replay-model.md` for Phase 03 decisions.

## Goals

- Canonical layer remains **replay-safe** relative to Phase 02 raw inputs.
- Canonical regeneration is **auditable** and **deterministic** under fixed versions.
- Operators can understand **why** outputs changed.

## Core vocabulary (disambiguated)

| Term | Definition |
| ---- | ---------- |
| **Phase 02 replay** | Re-ingestion / replay lane semantics at raw layer (Phase 01/02 domain). |
| **Canonical rebuild** | Deterministic recomputation of canonical projections from **already persisted** Phase 02 raw memory for a declared scope. Primary canonical correctness workload. |
| **Canonical regeneration** | Same raw snapshot, **new mapping bundle** (or new engine compat line), producing new canonical rows/version chains with explicit supersession. |
| **Canonical replay job** | Orchestrated rebuild/regeneration run with receipts (may chain Phase 02 verification hooks but distinct concern). |
| **Version pinning** | Explicit `mapping_bundle_id` selected for job; forbids silent drift across workers. |
| **Replay-safe remapping** | Guaranteed deterministic reproduction of transform lineage under declared bundle + compatibility rules (`phase-03-transform-lineage-doctrine.md`). |

## Inputs to canonical correctness

Canonical determinism is always conditioned on:

1. Phase 02 raw corpus slice (immutable append-only evidence),
2. **Pinned** `mapping_bundle_id` (+ compatibility profile when migrating),
3. Deterministic canonical engine build identifier,
4. Phase 02 trust posture when doctrine mandates halt/scopes down processing.

## Replay behavior (normative)

Given:

- Fixed Phase 02 raw corpus in scope,
- Fixed pinned `mapping_bundle_id`,
- Fixed deterministic engine build,

Then:

- Canonical **logical keys** and declared canonical ordering match rebuild oracle predictions (`phase-03-logical-key-doctrine.md`, `phase-03-temporal-timeline-doctrine.md`).

## Mutation boundaries

**Allowed**

- Append new canonical versions superseding prior versions with pointers.
- Insert new canonical rows for newly arrived raw evidence.
- Mark outputs invalid/stale with explicit enum reasons (`mapping_version_bump`, `raw_superseded`, `trust_gate`, `schema_correction`).

**Forbidden**

- In-place edits that orphan provenance.
- Deletes without tombstone + lineage (`phase-03-provenance-traceability-doctrine.md`).
- Clock-based identity creation.

## Idempotency (canonical layer)

Canonical writes must be idempotent on `(tenant_id, mapping_bundle_id, canonical_logical_key)` per object class (`phase-03-logical-key-doctrine.md`). Retries must not fork duplicates.

## Divergence taxonomy (canonical rebuild vs stored)

When rebuild oracle differs from persisted canonical rows:

| Class | Meaning | Action |
| ----- | ------- | ------ |
| **C0** | Bitwise-identical canonical projection set | PASS |
| **C1** | Equivalent under declared normalization / benign sorting | PASS (documented) |
| **C2** | Expected drift due to **approved** bundle migration / additive mapping | PASS with migration receipt |
| **C3** | Raw substrate / trust mismatch vs Phase 02 expectations | FAIL — fix Phase 02 / scope trust |
| **C4** | Canonical engine nondeterminism / key instability | FAIL — blocker |
| **C5** | Mapping bundle incompatibility undeclared (keys drift without compatibility line entry) | FAIL — registry governance |

**Forbidden drift:** silent reconcile to PASS when C3/C4/C5 — remediation doctrine applies.

## Version pinning rules

Authoritative resolution semantics: `phase-03-bundle-pinning-doctrine.md`.

- Every canonical materialization job logs **resolved bundle pin** after applying tenant defaults + policy overrides.
- **Active head** policy (always latest **approved** bundle) is **discouraged**; when permitted it **must** be implemented as an **explicit versioned policy artifact** (equivalent transparency to a pin)—never an implicit resolver default.
- **Forbidden:** implicit “latest bundle” selection for authoritative identity/order without such an artifact (**maps to floating mappings**).

## Transform compatibility

Bundle compatibility declarations MUST live in `phase-03-mapping-bundle-registry.md`. Breaking bumps without compatibility records are governance violations until remediated.

## Regeneration semantics

Regeneration **never** deletes historical canonical projections; it creates superseding rows/tombstones preserving lineage sufficient for audit (`phase-03-transform-lineage-doctrine.md`).

## References

- Bundle pinning (deterministic resolution): `phase-03-bundle-pinning-doctrine.md`
- Oracle vectors: `phase-03-oracle-vectors-doctrine.md`
- CI enforcement: `phase-03-ci-deterministic-enforcement-doctrine.md`
- Mapping registry: `phase-03-mapping-bundle-registry.md`
- Temporal ordering: `phase-03-temporal-timeline-doctrine.md`
- Closure gates: `phase-03-closure-gates-doctrine.md`
- Verification engine: `phase-03-verification-engine-doctrine.md`
