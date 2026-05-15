# Reasoning receipts & proof artifacts (Phase 06)

**Status:** normative schema intent (pre‑TypedDict freeze).

## Receipt types

| Receipt | Payload sketch |
|---------|----------------|
| `reasoning_chronology_receipt` | Hash of anchor chain + legality class + rule pack id. |
| `reasoning_causal_receipt` | Hash of sorted causal edge ids + degradation vector. |
| `reasoning_replay_receipt` | Input artifact hashes + permutation profile id + output hash. |
| `reasoning_ambiguity_receipt` | Ambiguity class + blocked derivation list hash. |
| `reasoning_equivalence_receipt` | Double‑run digest (see replay equivalence spec). |

## Hashing

Canonical JSON UTF‑8, sorted keys, `sha256` hex — same policy family as OCTS cert pack inner digest unless superseded by shared `REASONING_CANON_VERSION`.

## Storage posture

Append‑only ledgers preferred; tombstone via supersession row, not delete.

## CI

Structural validators ensure receipts present whenever corresponding artifact class is emitted.
