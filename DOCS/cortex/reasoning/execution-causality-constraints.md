# Execution causality constraints (Phase 06)

**Status:** constitutional constraints spec.

## Allowed derivation sources

- Explicit coordination kinds (`request`, `blocker`, `escalation`, `commitment`, …) from `execution_reconstruction_contracts.py`.  
- `ExecutionCoordinationEdge` paths of allowed `edge_kind`.  
- `NegativeExecutionSignal` and `FollowThroughGap` as **absence** evidence.  
- Phase **04** authoritative org links **only** where `link_authority` and temporal rules permit.

## Forbidden derivations

- “Implied cause” from message order alone without template/rule id.  
- Transitive closure across >N hops without explicit `transitive_rule_id` (N frozen per pack).  
- Merging partitions without `partitioned` outcome from conflict doctrine.

## Observed vs derived boundary

**Observed:** raw fields, connector enums.  
**Derived:** causal edges, interval completions.  
Every derived row lists **parent artifact ids** in sorted order for hash stability.
