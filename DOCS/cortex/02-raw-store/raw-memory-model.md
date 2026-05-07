# Raw Memory Model

## Definition
Raw memory is source-grounded, immutable, replayable evidence. It preserves what happened in source systems before canonical interpretation.

## Raw Memory Contains
- source payload snapshots,
- source identities and revisions,
- source timestamps and ordering hints,
- connector and ingestion metadata,
- replay lineage metadata,
- provenance bootstrap metadata.

## Raw Memory Does Not Contain
- canonical entities or relations,
- semantic topic labels,
- inferred ownership/causality,
- summarized discussion intelligence,
- graph abstractions.

## Design Consequence
Raw memory must optimize for:
- historical durability,
- deterministic retrieval,
- version-aware reprocessing,
- replay completeness verification.

## Trust Boundary
Raw memory is evidence truth, not semantic truth. Semantic truth is downstream and must always reference raw evidence.
