# Phase Dependency Graph

## Purpose
Describe blocking dependencies, contract prerequisites, ontology prerequisites, and replay propagation across phases.

## Dependency Chain
`01-ingestion` -> `02-raw-store` -> `03-canonical` -> `04-entity-resolution` -> `05-graph` -> `06-memory` -> `07-reasoning` -> `08-retrieval` -> `09-synthesis` -> `10-admin`.

## Phase Blocking Rules

### `01-ingestion` blocks `02-raw-store`
- Prerequisites:
  - envelope contract finalized,
  - connector auth/error semantics defined.
- Blockers:
  - undefined idempotency keys,
  - unstable envelope versioning.

### `02-raw-store` blocks `03-canonical`
- Prerequisites:
  - immutable raw write contract,
  - replay index strategy.
- Blockers:
  - retention/deletion ambiguity affecting replay baseline.

### `03-canonical` blocks `04-09`
- Prerequisites:
  - canonical ids and ontology slices stable,
  - mapping version semantics stable.
- Blockers:
  - unresolved ontology definitions,
  - unstable canonical relation typing.

### `04-entity-resolution` blocks `05-09`
- Prerequisites:
  - confidence model stability,
  - merge/split and conflict semantics finalized.
- Blockers:
  - unresolved identity conflict policy.

### `05-graph` blocks `06-09`
- Prerequisites:
  - temporal edge model,
  - dependency/ownership relation typing.
- Blockers:
  - undefined temporal validity semantics for edges.

### `06-memory` blocks `07-09`
- Prerequisites:
  - compaction policy,
  - derived view validity model.
- Blockers:
  - unresolved freshness and invalidation contracts.

### `07-reasoning` blocks `08-09` quality
- Prerequisites:
  - inference contract and confidence semantics.
- Blockers:
  - ambiguity policy not finalized.

### `08-retrieval` blocks reliable `09-synthesis`
- Prerequisites:
  - context-pack contract with provenance completeness criteria,
  - permission filtering guarantees.
- Blockers:
  - missing retrieval traceability metrics.

### `09-synthesis` depends on all prior guarantees
- Prerequisites:
  - confidence-to-language policy,
  - uncertainty disclosure requirements.
- Blockers:
  - citation policy unresolved.

### `10-admin` depends on full-system semantics
- Prerequisites:
  - operational RBAC model,
  - audit schema.
- Blockers:
  - undefined approval model for replay and policy overrides.

## Ontology Dependency Propagation
- Project/initiative/decision/concern definitions from ontology unlock consistent graph typing and reasoning semantics.
- Ontology instability in `03-canonical` propagates non-linearly into `05-09`.

## Replay Assumption Propagation
- Any replay contract drift in `02-04` invalidates downstream memory and inference comparability.
- Replay semantics are transitive; downstream phases cannot compensate for upstream replay ambiguity.
