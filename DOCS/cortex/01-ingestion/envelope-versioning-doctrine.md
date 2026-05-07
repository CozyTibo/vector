# Envelope Versioning Doctrine

## Purpose
Define how raw envelope versions evolve while preserving deterministic historical replay.

## Version Meanings
- `schema_version`: envelope contract structure and field semantics.
- `extraction_version`: deterministic normalization/extraction logic version.
- `processor_version`: ingestion processor behavior version.
- `replay_version`: replay policy context version.

## Core Doctrine
1. Version fields are part of replay lineage, not optional diagnostics.
2. Historical envelopes are immutable artifacts and are never rewritten in place.
3. New versions can generate new envelopes, but old envelopes remain auditable.
4. Replay differences must map to explicit version deltas.

## Additive Evolution Doctrine
- optional new fields may be introduced under existing major schema version when:
  - frozen core semantics are unchanged,
  - old readers remain compatible,
  - replay equivalence for unchanged fields remains stable.

## Breaking Evolution Doctrine
Breaking change means any change to frozen/replay-critical semantics.
Breaking changes require:
- schema version transition plan,
- replay impact statement,
- compatibility parser strategy,
- migration/replay rollout strategy with rollback.

## Old Envelope Handling
- old envelopes stay in raw store as immutable evidence,
- replay tooling remains version-aware for historical interpretation,
- audits can compare outputs across version contexts without data mutation.

## Implementation Readiness Threshold
Phase 01 can begin safely when:
- replay-critical semantics are frozen,
- version meanings are explicit and non-overlapping,
- schema evolution rules are enforceable,
- compatibility and replay policies are documented.
