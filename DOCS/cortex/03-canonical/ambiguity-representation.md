# Ambiguity Representation

## Purpose
Represent unresolved semantic uncertainty without forcing false certainty.

## Ambiguity Types
- uncertain ownership,
- uncertain topic linkage,
- conflicting interpretation candidates,
- partial semantic overlap across entities,
- unresolved identity equivalence hints.

## Representation Rules
- ambiguity is first-class record, not error side-effect.
- multiple hypotheses allowed with confidence metadata.
- ambiguity status lifecycle (`open`, `resolved`, `superseded`).

## Provenance Requirements
- each ambiguity record references supporting and conflicting evidence.

## Replay/Reprocessing
- ambiguity records persist across replay unless resolved by new evidence/policy.
- reprocessing can supersede ambiguity state, never erase history.
