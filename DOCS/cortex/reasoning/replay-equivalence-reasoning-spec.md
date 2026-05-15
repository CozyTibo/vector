# Replay equivalence for reasoning (Phase 06)

**Status:** normative spec.

## Obligations

Reasoning reducers that consume **OCTS walk artifacts** MUST:

1. Record `walk_result_hash` (or explicit “no walk” sentinel) in lineage.  
2. Declare **walk replay legality** snapshot at input time.  
3. If walk status is `replay_conflicted` or `replay_unverifiable`, output **matching** `replay_posture` on all dependent causal summaries.

## Double‑run law (target gate **G‑P06‑REPLAY‑01**)

Same inputs + same rule pack ⇒ identical `causal_chain_id` set for the tenant slice under test profile `reasoning_replay_permutation_v1`.

## Async jobs

If reasoning runs in Celery (future), permutation independence law mirrors **L‑EQ‑02** obligations — document in runtime matrix when implementation exists.
