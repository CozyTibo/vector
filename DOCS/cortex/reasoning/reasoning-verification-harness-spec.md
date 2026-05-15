# Reasoning verification harness spec (Phase 06)

**Status:** normative CI / harness spec (pre‑code).

---

## 1. Gate catalog — **measurable predicates** (v1)

Target family **`G‑P06‑*`** — each gate lists **inputs**, **pass condition**, **severity default**.

| Gate id | Inputs (frozen) | Pass condition | Default severity |
|---------|-----------------|----------------|------------------|
| **G‑P06‑ANTI‑01** | Reasoning package file tree | No forbidden imports/strings per ban table | `hard_fail` |
| **G‑P06‑PROV‑01** | Emitted artifact JSON schemas | All mandatory provenance keys present per [`reasoning-provenance-law.md`](./reasoning-provenance-law.md) | `hard_fail` |
| **G‑P06‑CHRON‑01** | `TemporalAnchorChain` snapshot + projection receipt | **§2.1** lookup succeeds; **`C`** equals lookup output after **§2.2**; **`(R, C)`** satisfies **CHRON‑FORB‑1** per [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md) | `hard_fail` |
| **G‑P06‑CAUS‑01** | Sorted `tcre_causal_edge_id` list | Each edge’s `tcre_causal_edge_kind` ∈ registry; `underlying_coordination_edge_ids` obey sentinel rules per [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md); default acyclicity | `hard_fail` |
| **G‑P06‑REPLAY‑01** | Golden case ×2 with permutation profile | Digests in §2 of [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md) match | `hard_fail` |
| **G‑P06‑AMB‑01** | `reasoning_ambiguity_receipt` | No unknown `ambiguity_class_id`; none cleared without supersession evidence | `hard_fail` |
| **G‑P06‑POL‑01** | Active policy pack JSON | Required keys + inequalities (`max_causal_hops_degraded` ≤ `max_causal_hops_default`) per [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) | `hard_fail` |
| **G‑P06‑BP‑01** | Breakpoint fixture | `breakpoint_index` byte‑stable per [`causal-breakpoint-detection-spec.md`](./causal-breakpoint-detection-spec.md) | `hard_fail` |
| **G‑P06‑CLOSE‑01** | Certification pack shape | Structural contract mirrors **G‑P05‑CLOSE‑01** shape (naming parity) | `hard_fail` |

**Staging:** Mirror **STAGE‑A…Z** pattern from Phase **05** CI enforcement architecture — **severity table** rows MAY cite gate ids above; until wired, treat as **doctrine‑frozen intent**.

---

## 2. Harness artifacts

Golden vectors under future `tests/.../reasoning_golden_vectors/v1/` — paths TBD at implementation; corpus alignment with [`../verification/golden-thread-replay-corpus-spec.md`](../verification/golden-thread-replay-corpus-spec.md).

---

## 3. Related

[`reasoning-runtime-legality-matrix.md`](./reasoning-runtime-legality-matrix.md) · [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md)
