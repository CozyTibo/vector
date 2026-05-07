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

## Unsupported Query Modes
- semantic search,
- topic clustering,
- graph traversal,
- organizational intelligence queries.

## Query Semantics
- deterministic selection criteria required.
- scope and ordering definitions must be explicit.
- query outputs are evidence sets, not interpreted conclusions.
