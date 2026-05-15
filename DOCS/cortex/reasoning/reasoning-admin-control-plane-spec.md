# Reasoning admin control plane (Phase 06)

**Status:** normative operator / admin spec (no UI code in this repo step).

---

## 1. Surfaces (mandatory at closure)

| Surface | Operator purpose |
|---------|------------------|
| **Reasoning health strip** | **`replay_safe_ordering`**, **`chronology_legality_class`**, **`replay_posture`**, **`causal_legality_class`**, sorted **`CD‑*`** rollup — **no collapsed single “green”** without all axes visible. |
| **Policy bundle inspector** | Active **`tcre_policy_pack_id`**, **`tcre_policy_bundle_digest`**, caps (`max_causal_hops_*`, transitive limits, breakpoint priorities). |
| **Temporal legality inspector** | Anchors, chains, skew flags, export order + **projection receipt** link. |
| **Causal chain debugger** | **`TCRECausalEdge_v1`** list / DAG with **`tcre_causal_edge_kind`**, **`underlying_coordination_edge_ids`**, hop‑level lineage to raw. |
| **Replay reasoning debugger** | Inputs: walk hashes, index epoch, **`reasoning_replay_permutation_v1`** JSON, policy digest → **canonical diff** of receipt digests (structural diff **P1** until specified). |
| **Chronology debugger** | Windows, half‑open intervals, silence **`silence_causality_rule_id`** sources. |
| **Ambiguity propagation inspector** | Canonical **`AMB‑*`** ids + blocked derivations (registry‑backed). |
| **Receipts explorer** | Reasoning receipts + proof artifacts (hashes). |
| **Causal contradiction topology** | Partition graph from conflict doctrine. |
| **Continuity breakpoints** | Cross‑system bridge failures + **`rank(S)`** display. |
| **Degradation topology** | **`CD‑*`** severity rollup by tenant / time window. |
| **Replay pressure** | Queue depth, job latency, equivalence failures count. |

---

## 2. Actions (policy‑gated)

Examples: **rebuild chronology** for tenant+bundle, **re‑emit causal chains** (dry‑run default), **quarantine slice** — each requires confirmation phrase + scope banner per [`../10-admin/dangerous-action-safety-model.md`](../10-admin/dangerous-action-safety-model.md).

---

## 3. RBAC

Align with admin permissions model; reasoning surfaces are **substrate** not end‑user intelligence.
