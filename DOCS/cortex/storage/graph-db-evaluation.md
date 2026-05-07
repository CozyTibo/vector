# Graph DB Evaluation

## Objective
Evaluate graph databases as a targeted response to measured traversal bottlenecks, not as default architecture.

## Potential Benefits
- lower-complexity deep path queries,
- strong ergonomics for lineage/continuity traversals,
- possible performance improvements for high-hop queries.

## Operational Costs
- additional datastore operations and on-call burden,
- synchronization and consistency complexity with primary truth store,
- replay/provenance dual-write and rebuild workflows,
- migration and backfill complexity.

## Risk To Cortex Principles
- provenance opacity if graph edges are not evidence-linked,
- replay nondeterminism if graph projections diverge,
- governance fragmentation across storage systems.

## Decision Criteria
Consider graph DB when:
- trust-critical traversal latency remains unacceptable after relational optimizations,
- deep traversal volume is persistent (not sporadic),
- synchronization model can be proven replay-safe and auditable.
