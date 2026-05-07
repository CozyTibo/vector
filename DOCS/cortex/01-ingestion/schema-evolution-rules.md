# Schema Evolution Rules

## Purpose
Allow safe envelope evolution without replay/provenance corruption.

## Allowed Changes
- additive optional metadata fields,
- namespaced connector-specific extension fields,
- observability enrichments that are non-authoritative,
- runtime diagnostics that are excluded from replay identity/equivalence logic.

## Forbidden Changes
- mutation of frozen identity semantics (`tenant_id`, connector identity fields, source identity semantics),
- mutation of temporal chronology semantics (`source_occurred_at` meaning),
- mutation/removal of replay lineage semantics (`replay_job_id`, `replay_version` meaning),
- removal of provenance minimums (`provenance.chain_id`, minimum `source_refs` continuity),
- mutation of ordering semantics used in deterministic replay,
- repurposing existing fields with new meaning under same `schema_version`.

## Backward Compatibility Rules
1. Old envelopes remain readable under version-aware parser paths.
2. Existing frozen field semantics must remain identical across versions.
3. New optional fields must have safe defaults for old readers.
4. Breaking behavior requires explicit major schema-version transition policy.

## Replay Compatibility Guarantees
- same source payload + same version tuple => equivalent envelope outputs,
- differences across runs must be attributable to explicit version tuple differences,
- replay must remain possible for historical envelopes without in-place mutation.

## Migration Expectations
- breaking changes require:
  - explicit schema version bump,
  - documented compatibility statement,
  - replay/migration plan for affected scopes,
  - divergence expectations and validation criteria.

## Version Pinning Expectations
- envelope writes must persist version tuple fields,
- readers must branch by `schema_version` when needed,
- replay jobs must pin version context and report it in lineage.
