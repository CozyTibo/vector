# Reasoning receipts & proof artifacts (Phase 06)

**Status:** normative schema intent (pre‑TypedDict freeze).

---

## 1. Receipt types

| Receipt | Payload sketch |
|---------|----------------|
| `reasoning_chronology_receipt` | Hash of anchor chain snapshot + **`replay_safe_ordering`** + projected **`chronology_legality_class`** + **`reasoning_rule_pack_id`** + **`tcre_policy_bundle_digest`** (see [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md)). |
| `reasoning_causal_receipt` | Hash of sorted **`tcre_causal_edge_id`** + sorted **`CD‑*`** list + **`causal_legality_class`**. |
| `reasoning_replay_receipt` | Input artifact hashes + **`reasoning_replay_permutation_v1`** payload + walk/index hashes + output hash. |
| `reasoning_ambiguity_receipt` | Sorted **`ambiguity_class_id`** (`AMB‑*`) + blocked derivation rules hash. |
| `reasoning_equivalence_receipt` | Double‑run digest (see [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md)). |

---

## 2. Hashing

Canonical JSON UTF‑8, sorted keys, `sha256` hex — same policy family as OCTS cert pack inner digest unless superseded by shared **`REASONING_CANON_VERSION`**.

---

## 3. Storage posture

Append‑only ledgers preferred; tombstone via supersession row, not delete.

---

## 4. CI

Structural validators ensure receipts present whenever corresponding artifact class is emitted.
