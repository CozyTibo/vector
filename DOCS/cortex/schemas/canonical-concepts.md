# Canonical Concepts

## Core Objects
- `CanonicalEvent`
- `CanonicalEntity`
- `CanonicalRelation`
- `CanonicalDecision`
- `CanonicalArtifact`
- `CanonicalThread`
- `CanonicalTopic`
- `CanonicalAction`

## Schema Expectations
Each concept must include:
- stable canonical identifier,
- tenant scope,
- temporal fields (`occurred_at`, `observed_at`, `processed_at`),
- provenance pointers to raw events,
- schema version,
- optional confidence metadata when interpretation is involved.

## Versioning
- Maintain additive evolution where possible.
- Breaking changes require migration and replay strategy.
- Canonical schema version must be embedded in persisted records.
