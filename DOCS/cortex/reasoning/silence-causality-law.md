# Silence → causality law (Phase 06)

**Status:** constitutional **freeze**.  
**Purpose:** Prevent colloquial **“quiet ⇒ blocked”** inference while allowing **only** explicit, receipted silence derivations.

---

## 1. Allowed sources

Lawful silence‑related TCRE inputs are **only**:

- **`ExecutionSilenceWindow`** records (`thread` \| `cross_system` \| `dependency_wait`) with **`derivation_rule_id`**.  
- **`NegativeExecutionSignal`** kinds that explicitly reference silence / unanswered patterns per **`NegativeSignalKind`** enum in **`execution_reconstruction_contracts.py`**.

---

## 2. Mapping — silence window → `tcre_causal_edge_kind`

| `ExecutionSilenceWindow.window_kind` | May produce `tcre_silence_window_obligation` | Additional requirement |
|----------------------------------------|-----------------------------------------------|---------------------------|
| `dependency_wait` | **Yes** | Must overlap (half‑open law) a **`depends_on`** or **`dependency_reference`** coordination window under same **`derivation_rule_id`** family. |
| `thread` | **Yes** | Must bind to **`thread_key`** + open **`request` \| `unresolved_ask` \| `follow_up`** lifecycle per frozen template **`silence_causality_rule_id`**. |
| `cross_system` | **Yes** | **Only** if every continuity bridge used for the silence obligation has **`rank(S) >= 4`** per [`cross-system-causal-continuity.md`](./cross-system-causal-continuity.md); else emit **`AMB‑BRIDGE‑weak`** and **no** causal edge. |

**Every** `tcre_silence_window_obligation` edge **MUST** carry **`silence_causality_rule_id`** (stable id in policy pack or template registry — version with policy pack).

---

## 3. Forbidden derivations

- Inferring **`tcre_coordination_block`** **solely** from “no messages for X seconds” without **`ExecutionSilenceWindow`** + rule id.  
- Upgrading silence to **`blocks`** without **`ExecutionCoordinationEdge`** with `edge_kind=blocks` or lawful negative‑signal path.  
- Using **`ExecutionVolatilityWindow`** or **`ExecutionReliabilityProfile`** axes to imply silence or block (see [`execution-causality-constraints.md`](./execution-causality-constraints.md) §Reliability firewall).

---

## 4. Negative signal path

When **`NegativeExecutionSignal`** lawfully references unanswered / silent patterns, emit **`tcre_negative_signal`** per [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md); **do not** duplicate as silence window edge unless both artifacts exist in evidence bundle (then link via lineage, single causal claim).

---

## 5. Replay

Silence edges participate in **`tcre_causal_edge_id`** hashing like any TCRE edge; permutation profiles **MUST** reorder raw arrival of silence‑closing events without changing sorted silence window ids in hash inputs — follow [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md).
