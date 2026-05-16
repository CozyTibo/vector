# Phase 06 — Specification gap matrix (TCRE)

**Status:** normative — **Active P0** empty; **constitutional doctrine `Frozen (doctrine)`** for Phase **06** Steps **1–35** as of **`P06-FINAL-FREEZE-2026-05-13`** (chronology closure, default policy fixture, harness alignment, implementation handoff). **Active P0** MUST remain empty unless a regression reopens a constitutional hole.  
**Role:** Same constitutional function as **[`../05-traversal/phase-05-spec-gap-matrix.md`](../05-traversal/phase-05-spec-gap-matrix.md)** — track **P0** / **P1** holes that block **`Frozen` (doctrine)** promotion for a step or slice.

**Normative program:** [`phase-06-normative-index.md`](./phase-06-normative-index.md).  
**Changelog:** [`PHASE06_CONSTITUTIONAL_CHANGELOG.md`](./PHASE06_CONSTITUTIONAL_CHANGELOG.md).  
**Implementation contract:** [`PHASE06_IMPLEMENTATION_HANDOFF.md`](./PHASE06_IMPLEMENTATION_HANDOFF.md).

---

## Active P0

*(none — cleared `P06-HARDEN-2026-05-13`; freeze pass `P06-FINAL-FREEZE-2026-05-13` — no new P0.)*

---

## Active P1

| ID | Topic | Owner |
| -- | ----- | ----- |
| **GAP‑P1‑P06‑02** | Operator **replay debugger** canonical diff (structural JSON vs hash‑only) | Admin spec |

---

## Resolved P1 (reference — do not delete)

| ID | Was | Resolution |
| -- | --- | ---------- |
| **GAP‑P1‑P06‑01** | Full **STAGE‑A…Z** row mapping for every **`G‑P06‑*`** vs Phase **05** CI arch doc | Shipped **`vector.domains.cortex.reasoning.reasoning_ci_enforcement_architecture`** (**P06‑31**): `reasoning_gp06_ci_full_stage_row_map_v1`, `verify_gp06_cia01`..`cia08`, topology runners; mirrors **Phase 05** doc anchor `phase-05-ci-enforcement-architecture.md` |

---

## Resolved P0 (reference — do not delete)

| ID | Was | Resolution document / section |
| -- | --- | ------------------------------ |
| **GAP‑P06‑P0‑01** | Causal edge vocabulary split vs `CoordinationEdgeKind` | [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md) Option **A** + updates to [`causal-reconstruction-doctrine.md`](./causal-reconstruction-doctrine.md), [`deterministic-causal-chain-spec.md`](./deterministic-causal-chain-spec.md), [`execution-causality-constraints.md`](./execution-causality-constraints.md) |
| **GAP‑P06‑P0‑02** | `replay_safe_ordering` vs `chronology_*` vs replay posture | [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md) + [`chronology-legality-law.md`](./chronology-legality-law.md) + [`temporal-reasoning-doctrine.md`](./temporal-reasoning-doctrine.md) |
| **GAP‑P06‑P0‑03** | Breakpoint multiset nondeterminism | [`causal-breakpoint-detection-spec.md`](./causal-breakpoint-detection-spec.md) §3–§6 |
| **GAP‑P06‑P0‑04** | Placeholder ambiguity vs corpus strings | [`ambiguity-registry-v1.md`](./ambiguity-registry-v1.md) + [`bounded-ambiguity-law.md`](./bounded-ambiguity-law.md) + [`../verification/golden-thread-replay-corpus-spec.md`](../verification/golden-thread-replay-corpus-spec.md) §3.2 |
| **GAP‑P06‑P0‑05** | Unmaterialized caps (`max_causal_hops_degraded`, transitive limits) | [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) |

---

## P2 (non-blocking refinements)

| ID | Topic | Owner |
| -- | ----- | ----- |
| **GAP‑P2‑P06‑01** | Operator replay debugger **structural JSON diff** canonicalization | Admin spec |
| **GAP‑P2‑P06‑02** | **`G‑P06‑POL‑01`** / other gates **pytest** wiring | Runtime (explicitly out of doctrine scope) |

---

## Strength legend

Mirrors **`../05-traversal/phase-05-spec-gap-matrix.md`** §Strength legend — **Frozen (doctrine)** here means the Phase **06** normative texts + canonical fixtures are closed for implementation (**no Active P0**); **`G‑P06‑*`** pytest wiring is **not** required for that label (**CI implemented** is separate); **runtime implemented** means shipped workers/APIs; **production‑certified** means **`reasoning-runtime-legality-matrix.md`** + operator closure milestones for the deployment class. Details: [`PHASE06_IMPLEMENTATION_HANDOFF.md`](./PHASE06_IMPLEMENTATION_HANDOFF.md).

---

## Per-step doctrine strength (post‑hardening snapshot)

| Step band | Default doctrine state | Notes |
| --------- | ------------------------ | ----- |
| 1–30 | **`Frozen (doctrine)`** | Registries, state machine, default policy fixture, replay laws, harness predicate text |
| 31–35 | **Strong** (doctrine text) / **Partial** (CI + tenant economics + closure pack **execution**) | **GAP‑P1‑P06‑01** (STAGE row map) **closed** in **P06‑31**; closure pack parity still unwired |

**Implementation authorization (constitutional):** Reducer, replay harness, runtime, and admin/control-plane **coding** MAY proceed under owner docs + [`PHASE06_IMPLEMENTATION_HANDOFF.md`](./PHASE06_IMPLEMENTATION_HANDOFF.md), subject to the **OCTS Steps 19–23** structural gate in [`phase-06-normative-index.md`](./phase-06-normative-index.md) for first **runtime package** integration.

---

## Amendments

Amendments **MUST** append a row:

| Date | ID | Change | Approver |
| ---- | -- | ------ | -------- |
| 2026‑05‑13 | **P06‑FINAL‑FREEZE‑2026‑05‑13** | Doctrine freeze candidate: **CHRON‑FORB‑1** closure via projection + default pack; registry xref; **`ReasoningPolicyPackV1_Default`**; **`PHASE06_IMPLEMENTATION_HANDOFF.md`**; tracker + harness alignment | Program lead |

---

## Review cadence

Any PR that weakens replay legality, provenance mandatory fields, or ambiguity survivability **MUST** update this file **before** merge.
