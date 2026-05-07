# Implementation Safety Gates

## Purpose
Define mandatory pre-implementation conditions per phase to prevent premature coding and architecture drift.

## Global Gates (Apply To All Phases)
- Ontology gate: required ontology concepts for the phase are stable.
- Contract gate: input/output contract fields and mutability are frozen for the implementation slice.
- Replay gate: replay behavior and version semantics are explicitly documented.
- Provenance gate: lineage obligations are complete and testable.
- Temporal gate: timestamp and validity-window semantics are unambiguous.
- AI boundary gate: allowed/forbidden AI behavior is explicit for the phase.

## Phase Gates

### `01-ingestion`
- Envelope schema finalized.
- Connector failure/backoff semantics finalized.
- No organizational inference pathways present.

### `02-raw-store`
- Immutable write protections finalized.
- Replay index and retention/deletion semantics finalized.

### `03-canonical`
- Canonical ontology slice ratified.
- Canonical ids and mapping version policy finalized.

### `04-entity-resolution`
- Confidence model and merge/split policy finalized.
- Conflict artifact schema finalized.

### `05-graph`
- Relation taxonomy finalized.
- Temporal validity semantics for edges finalized.

### `06-memory`
- Compaction policy and derived view catalog finalized.
- Rebuild/invalidation semantics finalized.

### `07-reasoning`
- Inference contract and ambiguity policy finalized.
- Causal hypothesis conflict handling finalized.

### `08-retrieval`
- Context-pack contract and provenance completeness criteria finalized.
- Access-filter semantics finalized.

### `09-synthesis`
- Citation and uncertainty language policy finalized.
- Confidence-to-language mapping finalized.

### `10-admin`
- Operational RBAC and audit schema finalized.
- Replay authorization and approval workflow finalized.

## Gate Failure Rule
If any required gate fails, implementation for that phase is blocked until resolution is documented and reviewed.
