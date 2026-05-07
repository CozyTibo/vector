# 06-memory Technical Decisions

## Required Decisions Before Implementation
- compaction windows and rollup grain
- derived view invalidation and rebuild triggers
- memory quality score model
- projection freshness guarantees

## Decision Constraints
- Decisions must preserve deterministic replay semantics.
- Decisions must not violate phase ownership boundaries.
- Cross-phase impact requires ADR linkage and contract versioning.
