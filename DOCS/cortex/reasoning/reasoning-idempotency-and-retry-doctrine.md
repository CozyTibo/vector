# Phase 06 — Idempotency and retry (reasoning replay lanes)

**Status:** **Partial** — constitutional **intent** only; keys, job envelopes, and reducer contracts ship with runtime.  
**Purpose:** Bind future **`vector.domains.cortex.reasoning`** (name TBD) replay lanes to the same **deterministic idempotency posture** as Phase **05** traversal — **without** duplicating OCTS walk semantics.

**Non‑normative for:** semantic dedupe, embedding caches, or “best effort” recomputation of causal graphs.

---

## Normative alignment

- **Structural precedent:** [`../05-traversal/phase-05-idempotency-and-retry-doctrine.md`](../05-traversal/phase-05-idempotency-and-retry-doctrine.md) — API + worker idempotency, canonical request hashing, retry classes.
- **Replay law:** [`replay-aware-reasoning-law.md`](./replay-aware-reasoning-law.md) — evidence bundle hash, rule pack id, **`tcre_policy_bundle_digest`**, permutation profile.
- **Proof / equivalence:** [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md) — **G‑P06‑REPLAY‑01** double‑run intent.

---

## Obligations (freeze at implementation)

1. **Logical keys** for reasoning jobs MUST include tenant identity + **scoped evidence bundle digest** + **`reasoning_rule_pack_id`** + **`tcre_policy_bundle_digest`** + **`engine_build_id`** (or successor) — same *class* of binding as OCTS (`engine_build_id` lineage).
2. **Replay lane isolation:** reasoning outputs written under `replay_job_id` (or successor column family) MUST NOT overwrite live‑lane rows; collision policy MUST be **fail‑closed** or **version‑append** per table class (define at schema freeze).
3. **At‑least‑once workers:** retries MUST be safe under identical inputs; **partial receipts** MUST be resumable or **explicitly abandoned** with a degradation receipt (**[`causal-degradation-spec.md`](./causal-degradation-spec.md)**).

---

## Forbidden

- Keying solely on wall‑clock “job start time.”
- Idempotency shortcuts that drop provenance, ambiguity class, or legality fields required by [`reasoning-provenance-law.md`](./reasoning-provenance-law.md).

---

## Gap tracking

Unresolved holes that block **`Frozen` (doctrine)** for this slice **MUST** be filed in [`reasoning-spec-gap-matrix.md`](./reasoning-spec-gap-matrix.md).
