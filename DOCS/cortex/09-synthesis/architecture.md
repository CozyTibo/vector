# Synthesis & Interaction Layer Architecture

## Input Contracts
- Bounded context packs
- Synthesis policy
- Audience/context intent

## Output Contracts
- Explainable synthesis responses
- Evidence chain references
- Uncertainty disclosures

## Allowed Logic
- Contract validation and schema version checks.
- Deterministic transformation inside declared ownership.
- Confidence annotation only when phase contract requires it.

## Forbidden Logic
- No fabrication beyond supplied evidence
- No hidden certainty escalation
- No bypass of retrieval boundaries

## Dependency Boundary
This phase depends only on upstream-adjacent contracts and shared schema definitions. Direct dependency on non-adjacent phase internals is forbidden.
