# Graph Traversal Cost Analysis

## Objective
Evaluate graph-like traversal pressure in Cortex while maintaining a relational-first posture.

## Traversal Classes
- local adjacency traversal (1-2 hops),
- deep recursive lineage traversal (N hops),
- temporal graph traversal (edge validity windows),
- ambiguity-aware branch traversal.

## Cost Drivers
- traversal depth,
- node fanout per hop,
- edge filter selectivity,
- temporal predicate complexity.

## Where Relational Is Strong
- shallow traversals with selective keys,
- consistency and replay-oriented write semantics,
- auditable deterministic transformations.

## Where Graph Pressure Emerges
- repeated deep path queries for incidents and audits,
- high-branch continuity reconstruction,
- path queries mixing temporal and provenance filters.

## Recommendation
Instrument traversal depth and fanout early; if deep traversal dominates trust-critical workflows, adopt targeted graph-style acceleration without abandoning relational truth.
