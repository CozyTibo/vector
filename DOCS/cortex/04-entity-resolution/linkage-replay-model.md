# Linkage Replay Model

## Replay Objective
Regenerate identity/linkage outcomes from canonical evidence under version-pinned policies.

## Replay Scope
- tenant + object/linkage scope + time window,
- optional continuity family scope (ownership/initiative/discussion).

## Replay Behavior
- regenerate linkages deterministically first, inferred second,
- preserve unresolved ambiguities unless new evidence resolves them,
- emit divergence report by linkage class and confidence shifts.

## Replay Safety
- no mutation of canonical/raw records,
- linkage supersession only, no destructive overwrite.
