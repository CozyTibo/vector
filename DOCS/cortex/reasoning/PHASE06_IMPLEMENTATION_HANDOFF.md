# Phase 06 (TCRE) — implementation handoff (runtime engineer contract)

**Status:** normative — **constitutionally frozen doctrine** as of bundle **`P06-FINAL-FREEZE-2026-05-13`** (see [`PHASE06_CONSTITUTIONAL_CHANGELOG.md`](./PHASE06_CONSTITUTIONAL_CHANGELOG.md)).  
**Audience:** reducer authors, replay harness authors, runtime service owners, admin/control-plane implementers.  
**Not in scope:** new law, new enums, env-based policy overrides, or deployment topology (those require a constitutional amendment).

**Read order:** [`phase-06-normative-index.md`](./phase-06-normative-index.md) → this document → owner docs cited below.

---

## A) What is constitutionally frozen

The **Phase 06** normative tree under **`DOCS/cortex/reasoning/`**, including at minimum:

- **Edge vocabulary:** closed **`tcre_causal_edge_kind`** + coordination mapping — [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md).  
- **Chronology ↔ replay bridge:** **`ChronologyLegalityProjectionV1`** + **CHRON‑FORB‑1** — [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md).  
- **Policy materialization + hash law:** pack shape, digest participation — [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md).  
- **Canonical default pack:** [`reasoning-policy-pack-v1-default.md`](./reasoning-policy-pack-v1-default.md) + [`fixtures/ReasoningPolicyPackV1_Default.json`](./fixtures/ReasoningPolicyPackV1_Default.json) + constant **`TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST`**.  
- **Ambiguity / degradation / silence:** [`ambiguity-registry-v1.md`](./ambiguity-registry-v1.md), [`causal-degradation-spec.md`](./causal-degradation-spec.md), [`silence-causality-law.md`](./silence-causality-law.md).  
- **Replay equivalence + permutation profile:** [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md).  
- **Provenance mandatory fields + receipts:** [`reasoning-provenance-law.md`](./reasoning-provenance-law.md), [`reasoning-receipts-and-proof-artifacts.md`](./reasoning-receipts-and-proof-artifacts.md).  
- **Harness predicate catalog (frozen intent):** [`reasoning-verification-harness-spec.md`](./reasoning-verification-harness-spec.md).

**Frozen (doctrine)** means: the text + fixtures above are the **sole** source of legality for implementation until a tracker‑reviewed amendment lands.

---

## B) What reducers must obey

- **Chronology:** derive **`chronology_legality_class`** **only** via **§2.1–§2.2** of [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md) against the **active** policy’s **`chronology_skew_projection_v1`**; **no match ⇒ fail closed**; emit **`reasoning_chronology_receipt`** with deterministic matched-row reference.  
- **Substrate immutability:** **CHRON‑AUTH‑1** — do not mutate **`TemporalAnchorChain`** in place.  
- **Causal edges:** emit only **`TCRECausalEdge_v1`** kinds from the registry; obey sentinel / cardinality rules per registry + [`deterministic-causal-chain-spec.md`](./deterministic-causal-chain-spec.md).  
- **Caps:** honor **`caps`**, **`replay_caps`**, **`breakpoint_rule_priority`**, **`merge_rules_coordination_edges`**, and related tables from the **active** pack — no ad hoc numeric limits.  
- **Digests:** every derived **`tcre_causal_edge_id`**, **`causal_chain_id`**, and chronology/replay/equivalence receipt inputs **MUST** include the active **`tcre_policy_bundle_digest`** per **CHRON‑POL‑1** in [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md).  
- **Ambiguity / degradation:** only registered **`AMB‑*`** / **`CD‑*`** semantics; monotonicity per [`causal-degradation-spec.md`](./causal-degradation-spec.md).

---

## C) What replay harnesses must verify

Implementations of the gate catalog **[`reasoning-verification-harness-spec.md`](./reasoning-verification-harness-spec.md) §1**, with **hard_fail** defaults unless a **documented waiver** applies:

- **G‑P06‑CHRON‑01:** §2.1 lookup + **CHRON‑FORB‑1** closure.  
- **G‑P06‑CAUS‑01 / G‑P06‑REPLAY‑01 / G‑P06‑AMB‑01 / G‑P06‑POL‑01 / G‑P06‑BP‑01** (and peers as wired).  
- **Golden / twin runs:** per [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md) — permutation independence and digest equality where specified.

Harnesses **MUST** pin **`tcre_policy_bundle_digest`** (default fixture digest unless the test case explicitly loads another pack and documents substitution).

---

## D) What runtime MAY NOT infer

- **No hidden cognition:** no LLM / similarity / probabilistic cause — [`phase-06-anti-goals-doctrine.md`](./phase-06-anti-goals-doctrine.md).  
- **No invented law:** no new **`tcre_causal_edge_kind`**, **`ambiguity_class_id`**, **`CD‑*`** cause codes, or tuple bridges outside owner docs.  
- **No silent policy:** changing effective caps/tables **without** bumping **`tcre_policy_pack_version`** and recomputing **`tcre_policy_bundle_digest`** is a **constitutional** failure.  
- **No alternate chronology path:** any code path that sets **`chronology_legality_class`** without the **§2.1** row match (+ **§2.2** when applicable) is invalid.

---

## E) What admin surfaces MUST expose

Per [`reasoning-admin-control-plane-spec.md`](./reasoning-admin-control-plane-spec.md) + chronology state machine **§8**:

- Active **`tcre_policy_pack_id`**, **`tcre_policy_bundle_digest`**, and **material caps** (operator-visible strip).  
- Side‑by‑side **contract `replay_safe_ordering`**, projected **`chronology_legality_class`**, **`replay_posture`**, **`CD‑*`** codes, and the **matched `chronology_skew_projection_v1` row** (or equivalent deterministic row reference).

---

## F) What artifacts participate in replay equivalence

Non-exhaustive list — authoritative detail in [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md) **§2** inner digest law:

- **`reasoning_chronology_receipt`**, **`reasoning_replay_receipt`**, **`reasoning_equivalence_receipt`** (when TCRE runs).  
- **`causal_chain_id`** and **`tcre_causal_edge_id`** hash inputs (include policy digest).  
- **`reasoning_replay_permutation_v1`** profile id where required.

---

## G) What policy artifacts MUST be loaded

- **Default:** [`fixtures/ReasoningPolicyPackV1_Default.json`](./fixtures/ReasoningPolicyPackV1_Default.json) — verify byte-stable digest equals **`TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST`** when that pack is active (**`G‑P06‑POL‑01`**).  
- **Alternate packs:** MUST conform to [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md); substitutions in tests or production **MUST** be explicit in receipts / waivers per **§4** of that doc.

---

## H) What constitutes a constitutional violation

- **Chronology:** **`(R, C)`** pair that violates **CHRON‑FORB‑1**; or **`C`** not equal to **§2.1** output (after **§2.2**); or missing row for a legal snapshot key.  
- **Registry:** unknown **`tcre_causal_edge_kind`** or mapping that contradicts [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md).  
- **Digest / id law:** derived ids or receipts that omit **`tcre_policy_bundle_digest`** or use a digest that does not match the serialized canonical pack body.  
- **Ambiguity / degradation:** unknown **`AMB‑*`** / **`CD‑*`**; cleared ambiguity without supersession evidence (**G‑P06‑AMB‑01**).  
- **Replay:** **G‑P06‑REPLAY‑01** mismatch across golden twin runs when the spec requires equality.

---

## RUNTIME tracks (post-doctrine)

| Track | Scope | Doc |
|-------|--------|-----|
| **RUNTIME-01** | Live bounded reconstruction: reducers, persistence, Celery, admin jobs/health, basic UI | (implementation in `vector.domains.cortex.reasoning.runtime`) |
| **RUNTIME-02** | Operator projections: chronology/edge/timeline/degradation explanations, replay structural diff, extended health | [`PHASE06_RUNTIME02_OPERATOR_VISIBILITY.md`](./PHASE06_RUNTIME02_OPERATOR_VISIBILITY.md) |
| **Substrate completeness** | Cross-pipeline omission ledger (ingestion → TCRE) | `vector.domains.cortex.completeness` + `GET .../cortex/substrate-completeness` + Cortex Overview pipeline UI |

**RUNTIME-02 APIs:** `GET .../runtime/jobs/{job_id}/operator-view`, `GET .../runtime/jobs/{job_id}/replay-diff`, extended `GET .../runtime/health`, `replay_diff` on replay-twin POST.

## Remaining non-blocking items (post-freeze)

Tracked explicitly (not blockers for starting reducers / harness / runtime / admin coding):

- **P1:** full **STAGE‑A…Z** row map for every **`G‑P06‑*`** vs Phase **05** CI architecture — [`reasoning-spec-gap-matrix.md`](./reasoning-spec-gap-matrix.md) **Active P1**.  
- **P1 / P2:** operator replay debugger **structural JSON diff** — **partially addressed** by RUNTIME-02 `replay_diff_projection.py` (bounded to in-memory twin runs; persisted artifact diff still P2).
