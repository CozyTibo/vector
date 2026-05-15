# Causal reconstruction doctrine (Phase 06)

**Status:** constitutional doctrine.  
**Defines:** **evidence‑bounded causal chains** — who blocked whom, what escalated from what, which commitment preceded which state change — **not** latent causal discovery.

## Causal primitive

A **causal edge** is admissible only if:

1. Endpoints are **ConversationExecutionEvent**, **ExecutionCommitment**, **CanonicalExecutionEntity**, or **NegativeExecutionSignal** instances already lawful under Phases **01–04** contracts; and  
2. The edge carries `derivation_rule_id`, `evidence_lineage`, and `DeterministicConfidenceSource`; and  
3. The edge kind is from a **closed enum** (e.g. `precipitated`, `blocked_by`, `escalated_from`, `resolved_by`, `superseded`) — implementation freezes the table.

## Forbidden causal edges

- Edges justified only by “usually happens after” co‑occurrence.  
- Edges across tenants.  
- Edges that require embedding similarity or topic clustering.

## Coexistence with Phase 05

Walk **paths** remain structural evidence. Phase **06** may consume **walk_result_hash** / hop receipts as **inputs** to causal stitching **only** when walk legality class is `replay_equivalent` or explicitly `replay_degraded` with receipt (see `replay-equivalence-reasoning-spec.md`).
