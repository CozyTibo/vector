# Causal reconstruction doctrine (Phase 06)

**Status:** constitutional doctrine.  
**Defines:** **evidence‑bounded causal chains** — who blocked whom, what escalated from what, which commitment preceded which state change — **not** latent causal discovery.

---

## 1. Causal primitive (frozen)

A **TCRE causal edge** is admissible only if it satisfies **`TCRECausalEdge_v1`** in [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md):

1. Endpoints are **`ConversationExecutionEvent`**, **`ExecutionCommitment`**, **`CanonicalExecutionEntity`**, or **`NegativeExecutionSignal`** (or **`FollowThroughGap`** / **`ExecutionSilenceWindow`** where sentinel rules apply) — all already lawful under Phases **01–04** contracts.  
2. **`tcre_causal_edge_kind`** is one of the **closed** enum values in the registry — **no** illustrative “e.g.” kinds; **no** values outside the registry version.  
3. **`underlying_coordination_edge_ids`** obey the sentinel and merge rules in the registry.  
4. Each edge carries **`derivation_rule_id`**, **`evidence_lineage`**, **`DeterministicConfidenceSource`**.

**Coordination substrate:** **`ExecutionCoordinationEdge`** / **`CoordinationEdgeKind`** remain **sole** coordination topology writers (Phases **01–03**). Phase **06** **never** mints new **`CoordinationEdgeKind`** literals.

---

## 2. Forbidden causal edges

- Edges justified only by “usually happens after” co‑occurrence.  
- Edges across tenants.  
- Edges that require embedding similarity or topic clustering.  
- Edges that violate [`silence-causality-law.md`](./silence-causality-law.md) or [`execution-causality-constraints.md`](./execution-causality-constraints.md) §Reliability firewall.

---

## 3. Coexistence with Phase 05

Walk **paths** remain structural evidence. Phase **06** may consume **`walk_result_hash`** / hop receipts as **inputs** only when walk legality class is **`replay_equivalent`** or **`replay_degraded`** with **`CD‑REPLAY`** linkage per [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md).

---

## 4. Escalation / dependency / blocker propagation

Propagation tables are **policy‑scoped** rows in [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) (`merge_rules_coordination_edges`, future **`propagation_rule_table_v1`**) — **no** ad hoc “tables (intent)” without ids.

---

## 5. Negative‑signal causality

**`NegativeExecutionSignal`** edges use **`tcre_negative_signal`** kind and sentinel **`__NO_COORDINATION_EDGE__`** when no coordination edge exists — lineage **must** close to signal + raw ids.

---

## 6. Related

[`execution-causality-constraints.md`](./execution-causality-constraints.md) · [`deterministic-causal-chain-spec.md`](./deterministic-causal-chain-spec.md)
