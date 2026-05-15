# Replay‑aware reasoning law (Phase 06)

**Status:** constitutional law.

---

## 1. Core obligation (pinned tuple)

Reasoning outputs MUST be functions of:

**(A)** raw evidence bundle digest,  
**(B)** **`reasoning_rule_pack_id`**,  
**(C)** **`tcre_policy_bundle_digest`** per [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md),  
**(D)** declared permutation profile id (**`reasoning_replay_permutation_v1`** or successor per [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md)),  
**(E)** when walks participate: **`walk_result_hash`** or **`__NO_WALK_INPUT__`**.

Same tuple ⇒ same deterministic **`tcre_causal_edge_id`** / **`causal_chain_id`** / receipt digests where equality is claimed.

---

## 2. Interaction with Phase 05

- **Async permutation:** causal summaries that ingest walk job order MUST declare dependency on **L‑EQ‑02** class posture from OCTS equivalence doctrine or mark **`replay_degraded`** + **`CD‑REPLAY`**.  
- **Index replay:** if derived index epoch participates, include **`index_content_hash`** receipt in lineage when required by [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md).

---

## 3. Forbidden

Using wall‑clock “processing time” as causal evidence. Using nondeterministic iteration order over unordered sets without sorted key rule. Omitting **`tcre_policy_bundle_digest`** from hash inputs where [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md) requires it.
