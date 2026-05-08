# Phase 03 — Canonical Logical Key Doctrine

**Status:** normative. Anchors **deterministic identity** for canonical rows independent of storage surrogate keys.

## Purpose

Define how **canonical logical keys** are derived so that:

- Retries/replays do not fork duplicates,
- Rebuild comparators have stable subjects,
- Mapping bundles can evolve with explicit compatibility semantics.

## Logical key vs surrogate key

| Term | Role |
| ---- | ---- |
| **Logical key** | Deterministic tuple derived from declared inputs; used for idempotency & equivalence. |
| **Surrogate id** | Opaque `canonical_*_id` stored in DB; stable once issued; must remain derivable from logical key + bundle id where required for audits. |

## Derivation rules (pattern)

For each canonical object class K:

1. Start from **tenant_id**.
2. Include **mapping_bundle_id** OR a declared **key_profile_version** sub-id when bundle allows multiple key shapes (must be explicit).
3. Include **connector** + **provider resource identity** fields present in raw (IDs, not guessed names).
4. Include **structural discriminant** for fan-out (e.g., mention index, segment ordinal) when 1→N.
5. Tie-break with **raw_record_id** only where provider lacks stable discriminant (documented per class).

**Forbidden:** timestamps, random UUIDs, worker hostnames, “now()”, hash of free-text without deterministic normalization table.

## Stability guarantees

- Under fixed `(raw_snapshot_slice, mapping_bundle_id)`, logical keys for emitted canonical rows are **stable** across machines (`phase-03-replay-versioning-doctrine.md`).
- Changing derivation rules **requires** new key profile or bundle bump—emit migration lineage (`phase-03-transform-lineage-doctrine.md`).

## Relationship to Phase 01 logical keys

- Phase 01 `source_identity_key` / `source_revision_key` may feed derivation inputs but **do not** replace canonical logical keys—canonical keys include mapping-specific discriminants.

## References

- Identity continuity (human/org): `phase-03-identity-continuity-doctrine.md`
- Registry: `phase-03-mapping-bundle-registry.md`
