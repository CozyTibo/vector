# Phase 06 (TCRE) — constitutional hardening changelog

**Purpose:** Pre‑implementation close‑out of hostile‑audit **P0** + selected **P1** items. **No runtime code** in this pass.

---

## 2026‑05‑13 — Final freeze + implementation handoff `P06-FINAL-FREEZE-2026-05-13`

### Chronology — **CHRON‑FORB‑1** closure (no model redesign)

- **Updated:** [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md) — **`ChronologyLegalityProjectionV1`** **§2.1** row lookup is the **sole** source of **`C`**; **CHRON‑FORB‑1** defined as closure over **§2.1–§2.2** + **§3** forbidden table; **§4** illustrative only; **§2.1** law text aligned (no “§3 exceptions” drift).

### Registry cross‑reference

- **Updated:** [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md) — cross‑system causal strength pointer → [`cross-system-causal-continuity.md`](./cross-system-causal-continuity.md) **§§1–2** (`rank(S)`), not an ordinal mismatch.

### Canonical default policy pack (first fixture)

- **New:** [`fixtures/ReasoningPolicyPackV1_Default.json`](./fixtures/ReasoningPolicyPackV1_Default.json) + [`reasoning-policy-pack-v1-default.md`](./reasoning-policy-pack-v1-default.md) — **`ReasoningPolicyPackV1_Default`**, **`TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST`**, canonical JSON + digest law, verifier hooks (**`G‑P06‑POL‑01`**, **`G‑P06‑CHRON‑01`**).
- **Updated:** [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) §8 — pointer to default fixture.

### Harness + program index

- **Updated:** [`reasoning-verification-harness-spec.md`](./reasoning-verification-harness-spec.md) — **`G‑P06‑CHRON‑01`** matches projection closure.  
- **Updated:** [`phase-06-normative-index.md`](./phase-06-normative-index.md) — dependency gate (**Steps 1–35** doctrine frozen + OCTS **19–23**); links to handoff + default pack; reading order leads with handoff.

### Tracker + gap matrix + handoff contract

- **New:** [`PHASE06_IMPLEMENTATION_HANDOFF.md`](./PHASE06_IMPLEMENTATION_HANDOFF.md) — runtime engineer contract (**A–H**).  
- **Updated:** [`reasoning-spec-gap-matrix.md`](./reasoning-spec-gap-matrix.md) — **Active P0** none; **`Frozen (doctrine)`** Steps **1–30**; strength legend distinguishes **Frozen (doctrine)** vs **runtime implemented** vs **CI implemented** vs **production‑certified**; implementation authorization note.  
- **Updated:** [`../MASTER_TRACKER.md`](../MASTER_TRACKER.md) — Phase **06** snapshot + blockers + readiness table + current focus (this bundle).

---

## 2026‑05‑13 — Hardening bundle `P06-HARDEN-2026-05-13`

### P0‑1 — Causal edge split brain

- **Adopted Option A:** distinct **`TCRECausalEdge_v1`** with closed **`tcre_causal_edge_kind`** enum and frozen **`CoordinationEdgeKind` → TCRE** map.  
- **New:** [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md).  
- **Updated:** [`causal-reconstruction-doctrine.md`](./causal-reconstruction-doctrine.md), [`deterministic-causal-chain-spec.md`](./deterministic-causal-chain-spec.md), [`execution-causality-constraints.md`](./execution-causality-constraints.md), [`reasoning-verification-harness-spec.md`](./reasoning-verification-harness-spec.md), [`MASTER_TRACKER.md`](../MASTER_TRACKER.md) Phase **06** rows.

### P0‑2 — Chronology / replay bridge

- **New:** [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md).  
- **Updated:** [`chronology-legality-law.md`](./chronology-legality-law.md), [`temporal-reasoning-doctrine.md`](./temporal-reasoning-doctrine.md), [`causal-degradation-spec.md`](./causal-degradation-spec.md), [`reasoning-provenance-law.md`](./reasoning-provenance-law.md).

### P0‑3 — Breakpoint determinism

- **Rewritten:** [`causal-breakpoint-detection-spec.md`](./causal-breakpoint-detection-spec.md) — multiset / undefined ordering **removed**; total order keys frozen.

### P0‑4 — Ambiguity registry

- **New:** [`ambiguity-registry-v1.md`](./ambiguity-registry-v1.md).  
- **Updated:** [`bounded-ambiguity-law.md`](./bounded-ambiguity-law.md), [`../verification/golden-thread-replay-corpus-spec.md`](../verification/golden-thread-replay-corpus-spec.md).

### P0‑5 — Policy pack

- **New:** [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md).  
- **Updated:** [`chronology-legality-law.md`](./chronology-legality-law.md), [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md), chain + edge registry docs.

### P1 (high priority) in same bundle

- **Cross‑system strength ordinal:** [`cross-system-causal-continuity.md`](./cross-system-causal-continuity.md).  
- **Corpus degradation ↔ `CD‑*`:** [`causal-degradation-spec.md`](./causal-degradation-spec.md).  
- **Silence causality:** new [`silence-causality-law.md`](./silence-causality-law.md).  
- **Reliability / volatility firewall:** [`execution-causality-constraints.md`](./execution-causality-constraints.md).  
- **Twin‑run scope + `reasoning_replay_permutation_v1`:** [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md).  
- **Gap matrix / index / tracker:** [`reasoning-spec-gap-matrix.md`](./reasoning-spec-gap-matrix.md), [`phase-06-normative-index.md`](./phase-06-normative-index.md).

### Cross‑document alignment (post‑hardening)

| Concept | Canonical owner | Consumers MUST NOT redefine |
|---------|-----------------|------------------------------|
| Coordination edge kinds | `execution_reconstruction_contracts.py` **`CoordinationEdgeKind`** | All TCRE docs |
| TCRE causal edge kinds | `tcre-causal-edge-registry-v1.md` | Causal / chain / replay / receipts |
| Chronology tuple law | `chronology-replay-legality-state-machine.md` | Chronology law, temporal doctrine, conflict temporal, provenance |
| Ambiguity ids | `ambiguity-registry-v1.md` | Bounded ambiguity law, golden thread, receipts |
| Degradation codes | `causal-degradation-spec.md` §1 + §3 | Provenance law, golden thread |
| Policy caps / digests | `reasoning-policy-pack-v1.md` | Edge ids, chain ids, replay tuple, chronology projection |
| Permutation profile | `replay-equivalence-reasoning-spec.md` §3 | Replay‑aware law, replay receipts |
| Silence → causal | `silence-causality-law.md` | TCRE registry, execution state law |

---

## Remaining P1 / P2 (tracker)

See [`reasoning-spec-gap-matrix.md`](./reasoning-spec-gap-matrix.md) **Active P1** + **P2** sections.

---

## Freeze‑status recommendations (post‑hardening)

| Slice | Recommended label | Rationale |
|-------|-------------------|-----------|
| Registries (`tcre` / `AMB` / policy / permutation §3) | **`Frozen (doctrine)`** (`P06-FINAL-FREEZE-2026-05-13`) | Closed enums + hash laws + default pack digest |
| Chronology state machine + default **`chronology_skew_projection_v1`** | **`Frozen (doctrine)`** | **CHRON‑FORB‑1** = closure over **§2.1–§2.2** + **§3** |
| Default policy fixture | **`Frozen (doctrine)`** | [`ReasoningPolicyPackV1_Default.json`](./fixtures/ReasoningPolicyPackV1_Default.json) |
| Harness STAGE wiring | **Partial** (**CI implemented** pending) | Active **P1** |
| Admin structural JSON diff | **P2** | Operator ergonomics |

---

## Registry ownership (summary)

| Registry | Owner doc | Version token |
|----------|-----------|----------------|
| TCRE causal edge kinds | `tcre-causal-edge-registry-v1.md` | `TCRE_CAUSAL_EDGE_REGISTRY_VERSION` |
| Ambiguity ids | `ambiguity-registry-v1.md` | `TCRE_AMBIGUITY_REGISTRY_VERSION` |
| Policy caps / tables | `reasoning-policy-pack-v1.md` + default [`reasoning-policy-pack-v1-default.md`](./reasoning-policy-pack-v1-default.md) | `TCRE_POLICY_PACK_VERSION` + `TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST` |
| Chronology tuples | `chronology-replay-legality-state-machine.md` | document hash + `tcre_policy_pack_version` inputs |
| Permutation profile | `replay-equivalence-reasoning-spec.md` | `reasoning_replay_permutation_v1` |
