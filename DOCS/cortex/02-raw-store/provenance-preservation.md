# Provenance Preservation

## Preservation Objective
Keep provenance continuity intact across replay, archival, evolution, and reprocessing.

## Provenance Truth Boundary
Provenance in Phase 02 proves chain-of-observation continuity:
- where evidence came from,
- when it was captured,
- under which run/replay context it persisted.

It does not prove semantic correctness of downstream interpretation.

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

## Representation of Gaps
When provenance is incomplete or damaged, the system must preserve explicit gap markers rather than silently implying continuity.
No best-effort inferred lineage may be presented as guaranteed provenance in Phase 02.
