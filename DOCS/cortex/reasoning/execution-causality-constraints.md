# Execution causality constraints (Phase 06)

**Status:** constitutional constraints spec.

---

## 1. Allowed derivation sources

- Explicit coordination kinds from **`ExecutionCoordinationKind`** in **`execution_reconstruction_contracts.py`**.  
- **`ExecutionCoordinationEdge`** with **`CoordinationEdgeKind`** only — mapped to **`TCRECausalEdge_v1`** per [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md).  
- **`NegativeExecutionSignal`**, **`FollowThroughGap`**, **`ExecutionSilenceWindow`** under [`silence-causality-law.md`](./silence-causality-law.md).  
- Phase **04** authoritative org links **only** where `link_authority` and temporal rules permit.  
- **`CommitmentLifecycle.state_history`** entries with explicit `rule_id`.

---

## 2. Forbidden derivations

- “Implied cause” from message order alone without template / **`derivation_rule_id`**.  
- Transitive closure beyond **`max_transitive_closure_hops`** from active [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) without **`transitive_rule_id`**.  
- Merging partitions without **`partitioned`** outcome from [`../continuity/conflict-resolution-doctrine.md`](../continuity/conflict-resolution-doctrine.md).

---

## 3. Observed vs derived boundary

**Observed:** raw fields, connector enums.  
**Derived:** **`TCRECausalEdge_v1`**, interval completions, chain ids.  
Every derived row lists **parent artifact ids** in **sorted** order for hash stability.

---

## 4. Causal legality class (`causal_legality_class`) — closed enum v1

| Value | Meaning |
|-------|---------|
| `causal_replay_equivalent` | All inputs walk/chronology/replay posture allow full chain. |
| `causal_replay_degraded` | Lawful chain under declared **`CD‑REPLAY`** / partial inputs. |
| `causal_chronology_blocked` | **`CD‑CHRON`** or forbidden tuple blocks strict causal claims. |
| `causal_ambiguous_partitioned` | Partitioned ambiguity — **`AMB‑PART‑storyline`**. |
| `causal_forbidden_substrate` | Illegal coordination / missing mandatory lineage. |
| `causal_unverifiable` | Honest cannot close — no guess. |

**Freeze:** amendments add rows here + bump **`TCRE_CAUSAL_EDGE_REGISTRY_VERSION`** or dedicated **`CAUSAL_LEGALITY_ENUM_VERSION`** in gap matrix.

---

## 5. Reliability / volatility firewall

**L‑REL‑1:** **`ExecutionReliabilityProfile`**, **`CoordinationReliabilityVector`**, **`ExecutionVolatilityWindow`**, and any **`*_rate_bps`**, **`*_score`**, or rubric axis **MUST NOT** be inputs to **`tcre_causal_edge_id`** derivation **unless** a **`derivation_rule_id`** explicitly listed in the policy pack names a **count‑only** mapping (e.g. “escalation count threshold exceeded” from **integer counts**, not latent scores).  
**L‑REL‑2:** Default is **forbid** — absence of an explicit allow‑list row means **no** reliability‑driven causal edges.

---

## 6. Related

[`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md) · [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md)
