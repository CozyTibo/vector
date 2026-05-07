# Dependency Mapping

## Critical Path
`connectors/ingestion` -> `raw_store` -> `canonical` -> `entity_resolution` -> `graph` -> `memory` -> `reasoning` -> `retrieval` -> `synthesis` -> `admin`.

## Contract Dependencies
- Canonical depends on immutable raw envelopes and replay indexes.
- Entity resolution depends on canonical identity surfaces.
- Graph depends on resolved entities and typed relations.
- Memory depends on graph + canonical continuity.
- Reasoning depends on temporal memory and uncertainty metadata.
- Retrieval depends on evidence lineage and access filtering.
- Synthesis depends on bounded context packs and confidence semantics.

## Readiness Dependencies
Implementation in a phase is blocked until:
- upstream contract versions are frozen for implementation slice,
- replay behavior for upstream phase is documented,
- failure surfaces are known and observable.

## Drift Prevention
Cross-phase contract changes must be versioned and announced before implementation work proceeds downstream.
