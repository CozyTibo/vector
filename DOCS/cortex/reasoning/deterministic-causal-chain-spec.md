# Deterministic causal chain spec (Phase 06)

**Status:** normative artifact contract (pre‑implementation).

## Causal chain object (conceptual)

- `causal_chain_id`: hash of sorted edge ids + rule pack id.  
- `edges`: ordered list of `{ from_ref, to_ref, edge_kind, derivation_rule_id }`.  
- `replay_posture`, `chronology_legality_class`, `ambiguity_class`, `degradation[]`.

## Equivalence

Two chains are **identical** iff canonical JSON bytes match per hashing policy in `reasoning-receipts-and-proof-artifacts.md`.

## Validation

Structural checks: acyclic unless `allowed_cycle_kinds` explicitly lists cycle type (default: none). Max hops enforced.
