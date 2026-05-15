# TCRE causal edge registry v1 (`TCRE_CAUSAL_EDGE_REGISTRY_VERSION`)

**Status:** constitutional **freeze** — Phase **06** **Option A** (distinct TCRE artifact).  
**Authority:** Substrate coordination edges remain **`ExecutionCoordinationEdge`** with **`CoordinationEdgeKind`** exactly as in **`execution_reconstruction_contracts.py`**. Phase **06** **MUST NOT** add literals to **`CoordinationEdgeKind`** or mutate coordination edges in place.

---

## 1. Constitutional model (frozen choice)

**Option A — adopted:** Phase **06** emits **`TCRECausalEdge_v1`** records that are **derivation artifacts** distinct from **`ExecutionCoordinationEdge`**. Every TCRE edge:

1. Uses **`tcre_causal_edge_kind`** from the **closed enum** §3 only (no free strings).  
2. Carries **`underlying_coordination_edge_ids`**: sorted unique list of **`edge_id`** values from **`ExecutionCoordinationEdge`**, **or** the explicit sentinel **`__NO_COORDINATION_EDGE__`** only when §4.2 permits non-edge evidence paths.  
3. Carries **`derivation_rule_id`**, **`evidence_lineage`**, **`DeterministicConfidenceSource`** per parent contracts.  
4. Never crosses tenants.

**Distinction (non‑negotiable):**

| Artifact | Role |
|----------|------|
| **`ExecutionCoordinationEdge`** | Phases **01–03** substrate: coordination topology between events (`CoordinationEdgeKind`). |
| **`TCRECausalEdge_v1`** | Phase **06**: **legality‑aware causal view** edges derived only via §3–§4; cite underlying coordination ids when they exist. |
| **Walk / OCTS hop receipts** | Phase **05**: **structural traversal evidence** — inputs to TCRE; **never** a substitute for §2 provenance on TCRE edges. |

---

## 2. Identifiers and hashing (replay)

- **`tcre_causal_edge_id`:** `derive_deterministic_id`‑style digest (implementation mirrors contracts) over canonical JSON of **sorted keys**: `namespace="tcre_causal_edge_v1"`, `parts` including `tcre_causal_edge_kind`, sorted `underlying_coordination_edge_ids`, `from_ref`, `to_ref`, `derivation_rule_id`, **`tcre_policy_bundle_digest`** (see [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md)), **`reasoning_rule_pack_id`**, tenant id.  
- **`causal_chain_id`:** per [`deterministic-causal-chain-spec.md`](./deterministic-causal-chain-spec.md) — **sorted list of `tcre_causal_edge_id`** + **`reasoning_rule_pack_id`** + **`tcre_policy_bundle_digest`** (same digest as on each edge for that run).  
- **Replay:** Changing **`CoordinationEdgeKind`** literals in contracts without bumping **`EXECUTION_RECONSTRUCTION_CONTRACT_VERSION`** is **out of law**; TCRE registry version bumps **only** via tracker‑approved amendment.

---

## 3. Closed enum — `tcre_causal_edge_kind` (v1)

| Kind | Meaning |
|------|---------|
| `tcre_coordination_escalation` | Causal view over coordination **`escalation_of`**. |
| `tcre_coordination_block` | Causal view over **`blocks`**. |
| `tcre_coordination_dependency` | Causal view over **`depends_on`**. |
| `tcre_coordination_handoff` | Causal view over **`handoff`**. |
| `tcre_coordination_thread_context` | Causal view over **`same_thread`** — **§5 restrictions apply**. |
| `tcre_coordination_temporal_order` | Causal view over **`temporal_successor`** — **ordering / packaging only**; **§5 restrictions apply**. |
| `tcre_commitment_transition` | From **`CommitmentLifecycle.state_history`** entries with explicit `rule_id` — **`underlying_coordination_edge_ids` MAY be `["__NO_COORDINATION_EDGE__"]`** if and only if lineage cites commitment + raw ids per §4.2. |
| `tcre_negative_signal` | From **`NegativeExecutionSignal`** + `derivation_rule_id` — sentinel allowed when no coordination edge exists. |
| `tcre_follow_through_gap` | From **`FollowThroughGap`** + rule — sentinel allowed. |
| `tcre_silence_window_obligation` | From **`ExecutionSilenceWindow`** **only** if [`silence-causality-law.md`](./silence-causality-law.md) **`silence_causality_rule_id`** is present — sentinel allowed. |

**Forbidden:** Any `tcre_causal_edge_kind` not in this table; any coordination **`edge_kind`** outside **`CoordinationEdgeKind`**; any TCRE edge **without** §2 mandatory fields.

---

## 4. Frozen mapping — `CoordinationEdgeKind` → `tcre_causal_edge_kind`

### 4.1 Primary map

| `CoordinationEdgeKind` (contract) | Primary `tcre_causal_edge_kind` |
|-----------------------------------|----------------------------------|
| `escalation_of` | `tcre_coordination_escalation` |
| `blocks` | `tcre_coordination_block` |
| `depends_on` | `tcre_coordination_dependency` |
| `handoff` | `tcre_coordination_handoff` |
| `same_thread` | `tcre_coordination_thread_context` |
| `temporal_successor` | `tcre_coordination_temporal_order` |

**Rule M‑INJ‑1:** For rows above, **`underlying_coordination_edge_ids`** MUST contain **exactly one** coordination `edge_id` unless a **declared merge rule** in the policy pack (see policy pack doc) permits a sorted multiset of ids for the **same** `tcre_causal_edge_kind` (merge rules are versioned; default is **one‑to‑one**).

### 4.2 Sentinel `__NO_COORDINATION_EDGE__`

Allowed **only** for kinds: `tcre_commitment_transition`, `tcre_negative_signal`, `tcre_follow_through_gap`, `tcre_silence_window_obligation`.  
If list is `[ "__NO_COORDINATION_EDGE__" ]`, **`evidence_lineage`** MUST still close to **raw** and/or **commitment / gap / silence** contract ids per **`execution_reconstruction_contracts.py`**.

---

## 5. Restrictions on “weak” coordination kinds

- **`tcre_coordination_thread_context`** and **`tcre_coordination_temporal_order`:** **MUST NOT** be the **sole** TCRE edge supporting a **cross‑system causal** claim. Cross‑system causality remains governed by [`cross-system-causal-continuity.md`](./cross-system-causal-continuity.md) (**`rank(S)`** ordinal — §§1–2).  
- **Forbidden pattern:** “temporal order implies block” without `tcre_coordination_block` or `tcre_negative_signal` (or lawful silence rule).

---

## 6. Admin / debug

Operator surfaces MUST show **both** `underlying_coordination_edge_ids` **and** `tcre_causal_edge_kind` — drilldown to coordination edge rows and raw lineage. Hiding coordination ids is **forbidden**.

---

## 7. Legality

- **`causal_legality_class`** on TCRE outputs is **orthogonal** to `tcre_causal_edge_kind`; enum freeze remains in [`execution-causality-constraints.md`](./execution-causality-constraints.md) §Causal legality.  
- Illegal substrate coordination edges **cannot** be “repaired” by emitting a different TCRE kind; emit **`causal_legality_class = causal_forbidden_substrate`** + **`CD‑REPLAY`** / conflict linkage per [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md) and [`execution-causality-constraints.md`](./execution-causality-constraints.md).

---

## 8. Related

[`causal-reconstruction-doctrine.md`](./causal-reconstruction-doctrine.md) · [`deterministic-causal-chain-spec.md`](./deterministic-causal-chain-spec.md) · [`execution-causality-constraints.md`](./execution-causality-constraints.md) · [`reasoning-receipts-and-proof-artifacts.md`](./reasoning-receipts-and-proof-artifacts.md)
