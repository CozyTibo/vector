# Chronology ↔ replay legality state machine (Phase 06)

**Status:** constitutional **freeze** — single bridge for **`TemporalAnchorChain.replay_safe_ordering`**, **`chronology_legality_class`**, **`replay_posture`** (artifact field per [`reasoning-provenance-law.md`](./reasoning-provenance-law.md)), **replay legality bundle** (golden thread §5), and **degradation codes** [`causal-degradation-spec.md`](./causal-degradation-spec.md).

**Default policy rows:** [`fixtures/ReasoningPolicyPackV1_Default.json`](./fixtures/ReasoningPolicyPackV1_Default.json) + [`reasoning-policy-pack-v1-default.md`](./reasoning-policy-pack-v1-default.md).

---

## 1. Authoritative sources (no dual writer)

| Layer | Authoritative writer | Field / artifact |
|-------|----------------------|------------------|
| **Substrate chronology (contract)** | Phases **01–04** reducers / materializations only | **`TemporalAnchorChain.replay_safe_ordering`** ∈ {`strict`, `partial`, `unresolved`} per **`execution_reconstruction_contracts.py`**. |
| **Phase 06 read‑only projection** | TCRE reducers | **`chronology_legality_class`** ∈ {`chronology_strict`, `chronology_partial`, `chronology_unresolved`, `chronology_degraded`} — **derived**, never written back into anchor chain rows. |
| **Replay bundle / walk** | Phase **05** + verification | **`replay_posture`** / **`expected_replay_legality_state`** per golden thread §5 and walk receipts. |

**CHRON‑AUTH‑1:** Phase **06** MUST NOT mutate **`TemporalAnchorChain`** in place. Downgrades are **append‑only** evidence + new chain rows / receipts per [`../continuity/conflict-resolution-doctrine.md`](../continuity/conflict-resolution-doctrine.md) §7.

---

## 2. `ChronologyLegalityProjectionV1` (deterministic — **sole source of `C`**)

### 2.0 Inputs

**Inputs (sorted, hashed in `reasoning_chronology_receipt`):**  
`snapshot = { anchor_chain_hash, replay_safe_ordering, skew_detected, late_arrival, export_sequence_conflict, active_conflict_classes[], tcre_policy_bundle_digest }`  

Booleans **`skew_detected`**, **`late_arrival`**, **`export_sequence_conflict`** MUST be the normalized substrate flags consumed by continuity / temporal conflict law (not ad hoc strings).

Let **`R`** = `snapshot.replay_safe_ordering`.

### 2.1 Algorithm (lookup — no informal “unless” branches)

1. Let **`policy`** be the parsed active policy pack JSON (see [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md)).  
2. Let **`rows`** = `policy["chronology_skew_projection_v1"]` (array of objects).  
3. Find the **unique** row **`m`** in **`rows`** such that:  
   `m["replay_safe_ordering"] == R` **and**  
   `bool(m["skew_detected"]) == bool(snapshot.skew_detected)` **and**  
   `bool(m["late_arrival"]) == bool(snapshot.late_arrival)` **and**  
   `bool(m["export_sequence_conflict"]) == bool(snapshot.export_sequence_conflict)`.  
4. If **no** row matches: **fail closed** — emit no `chronology_legality_class` on TCRE artifacts; **`G‑P06‑CHRON‑01`** / reducer **MUST** error (policy pack ill‑formed for this snapshot).  
5. Else: **`C` := `m["chronology_legality_class"]`** (must be one of the four `chronology_*` literals).  
6. Emit **`reasoning_chronology_receipt`** including digest of inputs + matched row id (row index in canonical sort order of `rows`, or embed row hash — implementation **MUST** choose one deterministic scheme and freeze in harness).

**Law:** There is **no** alternate path to **`C`** outside **§2.1–§2.2**; published **`(R, C)`** MUST satisfy **CHRON‑FORB‑1** (**§3**).

### 2.2 Partitioned exception (substrate truth)

If **`active_conflict_classes`** contains **`partitioned`** **and** the substrate has emitted the paired inspectability receipts required by [`../continuity/conflict-resolution-doctrine.md`](../continuity/conflict-resolution-doctrine.md), the **only** override permitted is: **replace** **`C`** with the value from the matching row that is tagged in policy with **`"partitioned_exception": true`** if such a row exists; **otherwise** keep **`C` from §2.1**. The default pack **does not** define partitioned rows — partitioned cases **MUST** ship an amended pack row set via constitutional amendment.

---

## 3. Forbidden tuples (hard constraints on published `(R, C)`)

Let **`C`** be the **`chronology_legality_class`** after §2.1 (and §2.2 if applicable).

| Tuple (`R`, `C`) | Verdict |
|------------------|---------|
| (`strict`, `chronology_unresolved`) | **FORBIDDEN** for publication **unless** §2.2 partitioned override applies. |
| (`unresolved`, `chronology_strict`) | **FORBIDDEN.** |
| (`partial`, `chronology_strict`) | **FORBIDDEN.** |
| (`strict`, `chronology_degraded`) | **FORBIDDEN** unless **`skew_detected`** is true **or** §2.2 applies. |

**CHRON‑FORB‑1 (closure):** A tuple **`(R, C)`** is **lawful** iff **`C`** is the output of **§2.1–§2.2** **and** **`(R, C)`** is **not** in the **FORBIDDEN** rows above without satisfying that row’s **exception** clause.

**Corollary:** The **default** fixture [`fixtures/ReasoningPolicyPackV1_Default.json`](./fixtures/ReasoningPolicyPackV1_Default.json) is constructed so **every** of the **24** boolean combinations yields a **`C`** satisfying **CHRON‑FORB‑1**. Custom packs **MUST** satisfy the same property or **fail closed** at load time.

---

## 4. Illustrative lawful outputs (non‑authoritative)

Typical outputs under the **default** pack include: **`(strict, chronology_strict)`**, **`(strict, chronology_degraded)`** when **`skew_detected`** is true, **`(strict, chronology_partial)`** when late/export flags apply without skew, **`(partial, chronology_partial)`** / **`(partial, chronology_degraded)`**, **`(unresolved, chronology_unresolved)`**. **Authoritative values** are always **§2.1 row lookup**.

---

## 5. `replay_posture` / golden thread replay legality

**Independent axis:** **`replay_posture`** answers walk/index/replay bundle equivalence, **not** pairwise event ordering.

**Frozen cross‑links:**

| `replay_posture` / golden §5 | Mandatory substrate posture |
|------------------------------|-------------------------------|
| `replay_equivalent` | Walk inputs (if any) MUST be `replay_equivalent`; anchor snapshot hash stable. |
| `replay_degraded` | Allowed with **`CD‑REPLAY`** + explicit walk/index receipt. |
| `replay_partial` | **MUST** list which artifact classes are excluded from equivalence. |
| `replay_unverifiable` | **MUST NOT** assert `chronology_strict` on outputs that depend on unverified walk slices. |
| `replay_conflicted` | **MUST** match [`organizational-continuity-reasoning.md`](./organizational-continuity-reasoning.md) walk conflict propagation. |

---

## 6. Degradation propagation

| Trigger | Code | Propagates to |
|---------|------|----------------|
| `chronology_partial` or `chronology_unresolved` or `chronology_degraded` | **`CD‑CHRON`** | Causal hop cap per policy; may force `causal_legality_class` downgrade. |
| `replay_degraded` / `replay_unverifiable` / `replay_conflicted` | **`CD‑REPLAY`** | TCRE outputs that consumed walks; **must** copy posture. |
| Weak / `unverifiable` continuity | **`CD‑CONT`** | Cross‑system causal edges blocked per continuity ordinal. |

Monotonicity: [`causal-degradation-spec.md`](./causal-degradation-spec.md).

---

## 7. Receipts and verifiers

- Every projection emits **`reasoning_chronology_receipt`** including **`ChronologyLegalityProjectionV1`** input digest + matched row reference.  
- **`G‑P06‑CHRON‑01`:** **`C`** equals **§2.1** lookup from active policy and **`(R, C)`** satisfies **CHRON‑FORB‑1**.  
- **Golden corpus:** `expected_chronology_legality_class` **MUST** equal **§2.1** output for the fixture’s `replay_safe_ordering` + flags in that case.

---

## 8. Admin visibility

Operators MUST see **side‑by‑side**: contract **`replay_safe_ordering`**, projected **`chronology_legality_class`**, **`replay_posture`**, active **`CD‑*`** codes, **policy pack id + digest**, and **matched `chronology_skew_projection_v1` row** — no single badge may collapse axes.
