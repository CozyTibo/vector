# Replay equivalence for reasoning (Phase 06)

**Status:** normative spec.

---

## 1. Obligations (walk consumers)

Reasoning reducers that consume **OCTS walk artifacts** MUST:

1. Record **`walk_result_hash`** (or explicit **`__NO_WALK_INPUT__`** sentinel) in lineage.  
2. Declare **walk replay legality** snapshot at input time (golden thread §5 classes).  
3. If walk status is **`replay_conflicted`** or **`replay_unverifiable`**, output **matching** **`replay_posture`** on all dependent causal summaries.

---

## 2. Double‑run law — **`G‑P06‑REPLAY‑01`** (frozen scope)

**Inputs pinned:** identical raw evidence bundle digest, **`reasoning_rule_pack_id`**, **`tcre_policy_bundle_digest`**, **`reasoning_replay_permutation_v1`** profile id.

**Outputs compared (byte‑stable digests):**

| Artifact / receipt | Required in equivalence? |
|--------------------|---------------------------|
| Set of **`causal_chain_id`** | **Yes** |
| **`reasoning_chronology_receipt`** canonical digest | **Yes** when chronology participates in reducer |
| **`reasoning_ambiguity_receipt`** digest | **Yes** if any **`ambiguity_class_id` ≠ `AMB‑NONE`** |
| **`reasoning_equivalence_receipt`** (inner double‑run digest) | **Yes** |
| **`reasoning_replay_receipt`** | **Yes** when walks/indexes consumed |
| Full proof bundle outer hash | **Optional** in v1 gate — **recommended hard_fail** when certification pack parity required |

**Law:** “Same `causal_chain_id` only” assertions are **insufficient** for **`G‑P06‑REPLAY‑01` hard_fail** once chronology or ambiguity receipts exist.

---

## 3. `reasoning_replay_permutation_v1` (fully specified)

**Intent:** Reorder **async ingestion job completion** for **independent** raw partitions without changing per‑record **`event_id`** / **`edge_id`** sets.

**Permutation object (conceptual):**

```json
{
  "profile_id": "reasoning_replay_permutation_v1",
  "partition_keys_sorted": ["github:connA", "slack:connB"],
  "within_partition_reverse": false,
  "shuffle_independent_partitions": true
}
```

**Laws:**

1. **Partition independence:** Permutation **MUST NOT** reorder two records that share a **`derivation_rule_id`**‑declared **happens‑before** edge in the **coordination substrate** (must consult sorted **`ExecutionCoordinationEdge`** list for the slice).  
2. **Stable sort fallback:** If independence test inconclusive, **lexicographic `raw_record_id`** order is the **only** lawful tie‑break.  
3. **Id output:** **`reasoning_replay_permutation_v1`** string **exactly** equals canonical JSON UTF‑8 of the object above with sorted keys — used in replay receipts.

**Permutation independence claim:** For profile above, **`causal_chain_id`**, chronology receipt digest, and ambiguity receipt digest **must** match across permutations when inputs (1) are otherwise identical and (2) policy pack unchanged.

---

## 4. Async jobs (Celery)

When workers exist, job completion order **must** satisfy §3 or mark **`replay_degraded`** + **`CD‑REPLAY`** — mirrors **L‑EQ‑02** class obligations from Phase **05** (cite walk equivalence doctrine); **no** wall‑clock ordering as evidence.

---

## 5. Related

[`replay-aware-reasoning-law.md`](./replay-aware-reasoning-law.md) · [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) · [`../verification/golden-thread-replay-corpus-spec.md`](../verification/golden-thread-replay-corpus-spec.md)
