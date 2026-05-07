# Canonicalization Storage Model

## Storage Objects
- canonical events table,
- canonical entities table,
- canonical relations table,
- canonical model-specific tables (topics/threads/artifacts/decisions/actions),
- ambiguity/conflict records,
- canonical replay divergence metadata.

## Persistence Boundaries
- write only canonical-layer outputs and metadata.
- never mutate raw-store records.
- ambiguity/confidence are persisted as first-class canonical metadata.

## Persistence Requirements
- include version tuple and provenance fields on all records.
- include temporal fields and validity windows where applicable.
