# Reasoning policy pack v1 (`TCRE_POLICY_PACK_VERSION`)

**Status:** constitutional **freeze** — authoritative caps and branch tables for Phase **06** reducers.  
**Role:** Materializes previously dangling knobs (**`max_causal_hops_degraded`**, transitive limits, chronology skew projection, replay caps) into a **versioned, hashable** artifact.

---

## 1. Policy bundle structure (conceptual)

| Field | Requirement |
|-------|-------------|
| `tcre_policy_pack_id` | Human‑readable id (e.g. `tcre_policy_default_v1`). |
| `tcre_policy_pack_version` | Monotonic integer or semver string; **bump** on any cap/table change. |
| `tcre_policy_bundle_digest` | `sha256` hex over **canonical JSON** (sorted keys) of the full pack body **excluding** this digest field. |

**Pack sections (required keys in canonical object):**

- **`caps`:** `max_causal_hops_default`, `max_causal_hops_degraded`, `max_transitive_closure_hops` (requires `transitive_rule_id` when >0), `max_breakpoints_per_chain`, `max_tcre_edges_per_chain`.  
- **`breakpoint_rule_priority`:** map of **`breakpoint_rule_id` → small integer priority** (lower fires first per [`causal-breakpoint-detection-spec.md`](./causal-breakpoint-detection-spec.md)).  
- **`chronology_skew_projection_v1`:** branch table for [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md) §2 degraded projection.  
- **`merge_rules_coordination_edges`:** optional list of `{ "merge_rule_id", "allowed_tcre_causal_edge_kind", "max_underlying_ids" }` — default **empty** (one‑to‑one).  
- **`replay_caps`:** optional limits on walk consumption (declarative only until runtime).

---

## 2. Hash participation (replay equivalence)

**CHRON‑POL‑1:** **`tcre_policy_bundle_digest`** MUST appear in:

- Every **`tcre_causal_edge_id`** payload (see [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md)).  
- Every **`causal_chain_id`** hash input (see [`deterministic-causal-chain-spec.md`](./deterministic-causal-chain-spec.md)).  
- **`reasoning_chronology_receipt`**, **`reasoning_replay_receipt`**, and **`reasoning_equivalence_receipt`** digests when TCRE reducers run.

**Law:** Changing policy **without** bumping digest ⇒ **different** deterministic ids — **replay equivalence** compares digests explicitly; **no silent “same chain”.**

---

## 3. Legality across policy versions

- **Same raw evidence + different policy version:** Outputs MAY differ; both runs MUST emit receipts listing **`tcre_policy_pack_id`** + digest.  
- **Equivalence tests (`G‑P06‑REPLAY‑01`):** Fixture pins **`tcre_policy_bundle_digest`**; runs with mismatched pack **fail closed** unless waiver documents pack substitution.

---

## 4. Overrides / waivers

- **`waivers/reasoning_verification_waivers.yaml`** (future path) MAY permit relaxed caps **only** with explicit waiver id stamped on **`reasoning_replay_receipt`**.  
- Production **`reasoning-runtime-legality-matrix.md`** predicates remain **normative**; waivers do not remove operator visibility.

---

## 5. Admin visibility

Operators MUST be able to view **active policy pack id + digest + caps** per tenant / job class — same strip as [`reasoning-admin-control-plane-spec.md`](./reasoning-admin-control-plane-spec.md).

---

## 6. Verifier expectations

- **G‑P06‑POL‑01 (future):** Structural validation — required keys present, integers ≥0, degraded hops ≤ default hops.  
- **G‑P06‑CHRON‑01:** Uses **`chronology_skew_projection_v1`** from active pack.

---

## 7. Relationship to Phase **01–05**

Policy pack **does not** alter **`CoordinationEdgeKind`** or **`TemporalAnchorChain`** writers; it only constrains **Phase 06 derivation**.

---

## 8. Canonical default fixture

Normative first pack: **[`reasoning-policy-pack-v1-default.md`](./reasoning-policy-pack-v1-default.md)** + **[`fixtures/ReasoningPolicyPackV1_Default.json`](./fixtures/ReasoningPolicyPackV1_Default.json)**.
