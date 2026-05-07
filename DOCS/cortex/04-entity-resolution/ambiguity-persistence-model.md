# Ambiguity Persistence Model

## Objective
Persist unresolved linkage ambiguity safely and inspectably.

## Ambiguity Types
- uncertain user linkage,
- uncertain initiative continuity,
- conflicting semantic links,
- partial ownership overlap,
- uncertain discussion continuity.

## Persistence Rules
- ambiguity records are first-class,
- competing hypotheses are stored side-by-side,
- ambiguity status lifecycle (`open`, `resolved`, `superseded`),
- confidence and provenance are mandatory.

## Replay Behavior
- unresolved ambiguity survives replay unless new evidence or versioned policy resolves it,
- historical ambiguity states remain auditable.
