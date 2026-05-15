# Causal breakpoint detection spec (Phase 06)

**Status:** normative spec — **deterministic replay‑safe** (post‑hardening).  
**Forbidden:** runtime‑native collection iteration order, hash‑map iteration, “natural” or “arrival” order without explicit sort keys, multiset without canonical serialization.

---

## 1. Breakpoint definition

A **causal breakpoint** is a **deduplicated** event or negative signal id at which **downstream causal influence** is legally truncated under a frozen **`breakpoint_rule_id`** (e.g. blocker resolution template matched, commitment terminal state, de‑escalation pattern).

---

## 2. Inputs (sorted before any pass)

1. **`events`:** all **`ConversationExecutionEvent`** ids participating in the chain slice, sorted lexicographically by **`event_id`**.  
2. **`signals`:** all **`NegativeExecutionSignal.signal_id`** values sorted lexicographically.  
3. **`tcre_edges`:** list of **`tcre_causal_edge_id`** sorted lexicographically.  
4. **`policy`:** active **`tcre_policy_bundle_digest`** (caps include **`max_breakpoints_per_chain`**).

---

## 3. Active frontier (ordered list, not multiset)

**Definition:** The **active causal frontier** at step *k* is an **ordered list** `F_k` of vertex ids (events or signals), **without duplicates**, constructed deterministically:

**Insertion rule:** When an edge `u → v` becomes “active,” insert **`v`** into `F_k` using **stable sort** by key:

`primary_sort = (observed_at_iso, raw_record_id_min, vertex_id_string)`

where **`raw_record_id_min`** is the minimum **`source_raw_record_ids`** element on the vertex payload (must exist; else **`CD‑CHRON`** and vertex is ineligible for frontier — emit degradation and **skip** insertion).

**Removal rule:** When a **`breakpoint_rule_id`** fires on vertex `x`, remove **`x`** and every vertex **reachable from** `x` via **active** `tcre_coordination_*` edges only, using **reverse lexicographic** removal order on ids to avoid implementation drift.

**Law BP‑ORD‑1:** At no time may the frontier be represented as an unordered multiset. The **only** lawful structure is **sorted unique list** with the key above.

---

## 4. Forward pass algorithm (deterministic)

```
F := empty ordered list
for each edge e in tcre_edges_sorted_by (from_ref, to_ref, tcre_causal_edge_id):  # lexicographic triple
    apply edge activation per derivation rules
    maintain F per §3 insertion rule
    evaluate breakpoint predicates in order of increasing (breakpoint_rule_priority_int, breakpoint_rule_id)
    on fire: append to breakpoint_list; mutate F per §3 removal rule
```

**`breakpoint_rule_priority_int`:** frozen small integers in policy pack (`reasoning-policy-pack-v1.md`); **lower fires first**.

---

## 5. Outputs

| Output | Definition |
|--------|------------|
| `breakpoint_index` | List of `{ "breakpoint_id", "rule_id", "at_vertex_id" }` sorted by `(observed_at_iso, at_vertex_id, rule_id)`. |
| `breakpoint_id` | `sha256` hex over canonical JSON of `{ "rule_id", "at_vertex_id", "frontier_snapshot_digest_pre", "frontier_snapshot_digest_post", "tcre_policy_bundle_digest" }`. |
| `before_chain_id` / `after_chain_id` | Optional chain splits — ids themselves hashed per [`deterministic-causal-chain-spec.md`](./deterministic-causal-chain-spec.md). |

---

## 6. Replay and permutation guarantees

- **Permutation independence:** Reordering **ingestion job completion** for **independent** raw rows **must not** change **`breakpoint_index`** if **`event_id`** and **`tcre_causal_edge_id`** sets are identical — same law class as **`reasoning_replay_permutation_v1`** in [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md).  
- **CI:** **`G‑P06‑BP‑01` (future)** asserts byte‑stable **`breakpoint_index`** on golden fixture.

---

## 7. Non‑goals

Velocity, sentiment, or “team slowed down” without countable **`NegativeExecutionSignal`** / silence window evidence per [`silence-causality-law.md`](./silence-causality-law.md).
