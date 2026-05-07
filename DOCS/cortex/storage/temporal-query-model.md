# Temporal Query Model

## Temporal Objective
Support reliable reconstruction of "what was true when" across evolving states, supersessions, and replay windows.

## Temporal States To Support
- current effective state,
- historical as-of state,
- superseded state chains,
- transition timelines for ownership, initiative, and decisions.

## Canonical Temporal Dimensions
- source occurrence time (`occurred_at`),
- processing time (ingest/transform time),
- validity interval (`effective_from`, `effective_to`),
- replay lifecycle timestamps.

## Query Patterns
- as-of reconstruction for incident/debug windows,
- delta windows (what changed in [t1, t2]),
- continuity timelines for actor/initiative shifts,
- supersession lineage expansion.

## Indexing Implications
- composite indexes including tenant + scope + temporal dimensions,
- selective support for interval overlap predicates,
- temporal-ordering support for replay and timeline scans.

## Risks
- interval joins become expensive with wide windows,
- supersession chains increase traversal depth over years,
- occurrence-time vs processing-time confusion causes incorrect reconstructions.

## Guardrail
Temporal semantics must remain explicit and queryable without hidden assumptions; every time axis used by operators must be documented and indexed deliberately.
