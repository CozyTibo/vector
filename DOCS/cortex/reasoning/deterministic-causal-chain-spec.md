# Deterministic causal chain spec (Phase 06)

**Status:** normative artifact contract (pre‑implementation).  
**Normative edge unit:** **`TCRECausalEdge_v1`** per [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md) — **not** raw **`ExecutionCoordinationEdge`** rows alone.

---

## 1. Causal chain object (conceptual)

| Field | Law |
|-------|-----|
| `causal_chain_id` | Hash over **canonical JSON** (sorted keys) of: sorted list **`tcre_causal_edge_id`**, **`reasoning_rule_pack_id`**, **`tcre_policy_bundle_digest`**, tenant id. |
| `tcre_edges` | Ordered list of **`tcre_causal_edge_id`** sorted **lexicographically** (list order is this sort — **not** ingestion order). |
| `replay_posture` | Golden thread §5 class. |
| `chronology_legality_class` | From [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md). |
| `ambiguity_class_id` | From [`ambiguity-registry-v1.md`](./ambiguity-registry-v1.md) (`AMB‑NONE` explicit). |
| `degradation[]` | `CD‑*` codes per [`causal-degradation-spec.md`](./causal-degradation-spec.md), sorted by `(code, rule_id)`. |

---

## 2. Equivalence

Two chains are **identical** iff `causal_chain_id` matches **and** sorted **`tcre_causal_edge_id`** lists match.

---

## 3. Validation

- **Acyclicity:** default **no cycles**; if policy introduces lawful cyclic templates, **`allowed_cycle_kinds`** MUST list them with **`cycle_normalization_rule_id`**.  
- **Hop caps:** **`max_causal_hops_*`** from [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md).  
- **Breakpoints:** optional index per [`causal-breakpoint-detection-spec.md`](./causal-breakpoint-detection-spec.md); **`breakpoint_id`** hashes **do not** replace `causal_chain_id` — they attach as child receipts.

---

## 4. Twin‑run equivalence scope

Per [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md) §5 — **`G‑P06‑REPLAY‑01`** compares at minimum **`causal_chain_id`** **and** **`reasoning_chronology_receipt` digest** **and** sorted **`reasoning_ambiguity_receipt`** digest when any ambiguity ≠ `AMB‑NONE`.

---

## 5. Related

[`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md) · [`reasoning-receipts-and-proof-artifacts.md`](./reasoning-receipts-and-proof-artifacts.md)
