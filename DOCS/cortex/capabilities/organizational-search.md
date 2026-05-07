# Organizational Search Capability

Organizational search in Cortex is continuity-aware reconstruction, not document keyword search.

## Query Classes

- Why was rollout X delayed?
- What discussions and decisions led to architecture Y?
- Who influenced migration Z and when?
- What changed between initial and final implementation plans?

## Required Architecture Primitives

- canonical entities and relations (actors, initiatives, decisions, blockers, artifacts),
- temporal query primitives (as-of, interval, transition windows),
- cross-tool linkage for actor/artifact continuity,
- provenance-exposed search results,
- retrieval ranking that respects evidence quality and recency.

## Trust Model

Search results must include:

- evidence references,
- confidence markers,
- ambiguity notes,
- replay/version context where relevant.

## Failure Modes To Guard

- aliasing errors across actor identities,
- timeline compression that hides sequence,
- over-ranked inferred links with weak evidence.

## Phase Dependence

- Minimum feasible: phases 01-07.
- Operationally useful at scale: phases 01-08.
