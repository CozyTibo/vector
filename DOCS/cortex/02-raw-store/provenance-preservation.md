# Provenance Preservation

## Preservation Objective
Keep provenance continuity intact across replay, archival, evolution, and reprocessing.

## Must-Preserve Provenance Fields
- provenance chain id,
- source reference ids,
- connector/source identity metadata,
- ingestion/replay version context,
- durable raw event identifiers.

## Ingestion Stability Dependency
Phase 02 provenance continuity depends on Phase 01 frozen-core envelope contracts:
- stable replay lineage semantics,
- stable identity and chronology semantics,
- stable provenance minimum fields.
Reference: `../01-ingestion/raw-envelope-contract-stability.md`.

## Preservation Across Lifecycle
- replay: provenance fields copied forward, never rewritten.
- archival: provenance remains queryable even if payload moved cold.
- schema evolution: provenance compatibility maintained.
- reprocessing: provenance maps regenerated outputs to raw source records.

## Non-Negotiable Rule
Any operation that removes provenance continuity is considered a critical architecture violation.
