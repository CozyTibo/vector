# Raw Memory Query Model

## Supported Query Modes
- source-oriented:
  - by source identity, source object, connector, revision.
- replay-oriented:
  - by tenant/connector/time scope and replay context.
- audit-oriented:
  - by ingestion run, replay job, mutation/integrity events.
- provenance-oriented:
  - by provenance chain/source refs.
- temporal-oriented:
  - as-of retrieval, latest-known-before-T, revision-chain retrieval.

Queryability in Phase 02 is evidence retrieval only:
- evidence sets,
- lineage sets,
- temporal slices,
- replay/provenance scoped retrieval.

## Unsupported Query Modes
- semantic search,
- topic clustering,
- graph traversal,
- organizational intelligence queries.
- causal/ownership conclusions,
- execution-intelligence derivation.

## Query Semantics
- deterministic selection criteria required.
- scope and ordering definitions must be explicit.
- query outputs are evidence sets, not interpreted conclusions.

## Anti-Goal Guardrail
Any query contract that implies organizational interpretation belongs to later phases and must not be added to Phase 02.

## Binary Conformance Requirement
Supported query classes and anti-goal enforcement are closure-gated by `binary-closure-gates.md` (G7).
