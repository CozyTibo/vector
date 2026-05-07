# Storage Strategy

## Postgres-First Position
PostgreSQL on AWS RDS is the sole required persistent substrate for initial Cortex delivery. This decision optimizes operational simplicity while supporting event persistence, relational integrity, JSONB payloads, and replay indexing.

## Memory Layer Mapping To Storage
- Raw memory: append-only event tables + envelope metadata.
- Canonical memory: normalized event/entity/relation tables with version fields.
- Graph memory: temporal edges and node-link histories.
- Derived memory: denormalized query-optimized projections.
- Semantic memory: optional embedding/index side tables.

## Write Semantics
- Raw writes are immutable.
- Canonical corrections are superseding records.
- Derived layers are rebuildable from canonical + graph lineage.
- Inference layers are explicitly versioned and replayable.

## Deferral Policy
S3 archival, pgvector acceleration, OpenSearch, or graph database adoption requires workload evidence and ADR approval; none are baseline dependencies.
