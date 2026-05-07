# Temporal/Causal Intelligence Layer Architecture

## Input Contracts
- Derived memory
- Temporal graph
- Inference policies

## Output Contracts
- Reasoning artifacts
- Causal hypothesis sets
- Uncertainty markers

## Allowed Logic
- Contract validation and schema version checks.
- Deterministic transformation inside declared ownership.
- Confidence annotation only when phase contract requires it.

## Forbidden Logic
- No canonical fact rewriting
- No certainty claims without confidence support
- No connector-specific semantic logic

## Dependency Boundary
This phase depends only on upstream-adjacent contracts and shared schema definitions. Direct dependency on non-adjacent phase internals is forbidden.
